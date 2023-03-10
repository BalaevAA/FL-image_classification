#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python version: 3.6

import copy
import numpy as np
from torchvision import datasets, transforms
import torch

from utils.sampling import cifar_iid, cifar_noniid
from utils.options import args_parser
from models.Update import LocalUpdate
from models.Nets import vgg16, CNNCifar
from models.Fed import FedAvg
from models.Test import test_img
from utils.util import setup_seed
from datetime import datetime
from tqdm import tqdm


if __name__ == '__main__':
    # parse args
    args = args_parser()
    args.device = torch.device('cuda:{}'.format(args.gpu) if torch.cuda.is_available() and args.gpu != -1 else 'cpu')
    setup_seed(args.seed)


    # load dataset and split users
    if args.dataset == 'cifar':
        transform_train = transforms.Compose([
            transforms.RandomCrop(32, padding=4),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
        ])
        transform_test = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
        ])
        dataset_train = datasets.CIFAR10('../data/cifar', train=True, download=True, transform=transform_train)
        dataset_test = datasets.CIFAR10('../data/cifar', train=False, download=True, transform=transform_test)
    else:
        exit('Error: unrecognized dataset')

    if args.iid:
        dict_users = cifar_iid(dataset_train, args.num_users)
    else:
        dict_users, _ = cifar_noniid(dataset_train, args.num_users, args.alpha)

    # build model
    if args.model == 'lenet' and args.dataset == 'cifar':
        net_glob = CNNCifar(args=args).to(args.device)
    elif args.model == 'vgg' and args.dataset == 'cifar':
        net_glob = vgg16().to(args.device)
    else:
        exit('Error: unrecognized model')
    print(net_glob)
    net_glob.train()

    # copy weights
    w_glob = net_glob.state_dict()

    # training
    loss_train = []
    cv_loss, cv_acc = [], []
    val_loss_pre, counter = 0, 0
    net_best = None
    best_loss = None
    val_acc_list, net_list = [], []
    test_best_acc = 0.0

    for iter in range(args.epochs):
        w_locals, loss_locals = [], []
        m = max(int(args.frac * args.num_users), 1)
        idxs_users = np.random.choice(range(args.num_users), m, replace=False)
        for idx in tqdm(idxs_users):
            local = LocalUpdate(args=args, dataset=dataset_train, idxs=dict_users[idx])
            w, loss = local.train(net=copy.deepcopy(net_glob).to(args.device))
            w_locals.append(w)
            loss_locals.append(loss)
        # update global weights
        w_glob = FedAvg(w_locals)

        # copy weight to net_glob
        net_glob.load_state_dict(w_glob)

        # print loss
        loss_avg = sum(loss_locals) / len(loss_locals)
        print('Round {:3d}, Train loss {:.3f}'.format(iter, loss_avg))
        loss_train.append(loss_avg)

        test_acc, test_loss = test_img(net_glob, dataset_test, args)


    # testing
    net_glob.eval()
    acc_train, loss_train = test_img(net_glob, dataset_train, args)
    acc_test, loss_test = test_img(net_glob, dataset_test, args)
    print("Training accuracy: {:.2f}".format(acc_train))
    print("Testing accuracy: {:.2f}".format(acc_test))
