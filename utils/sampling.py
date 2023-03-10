#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python version: 3.6


import numpy as np
from torchvision import datasets, transforms
from collections import defaultdict
import random


def cifar_iid(dataset, num_users):
    """
    Sample I.I.D. client data from CIFAR10 dataset
    :param dataset:
    :param num_users:
    :return: dict of image index
    """
    num_items = int(len(dataset)/num_users)
    dict_users, all_idxs = {}, [i for i in range(len(dataset))]
    for i in range(num_users):
        dict_users[i] = set(np.random.choice(all_idxs, num_items, replace=False))
        all_idxs = list(set(all_idxs) - dict_users[i])
    return dict_users


def cifar_noniid(dataset, no_participants, alpha=0.9):
    """
    Input: Number of participants and alpha (param for distribution)
    Output: A list of indices denoting data in CIFAR training set.
    Requires: cifar_classes, a preprocessed class-indice dictionary.
    Sample Method: take a uniformly sampled 10-dimension vector as parameters for
    dirichlet distribution to sample number of images in each class.
    """
    np.random.seed(666)
    random.seed(666)
    cifar_classes = {}
    for ind, x in enumerate(dataset):
        _, label = x
        if label in cifar_classes:
            cifar_classes[label].append(ind)
        else:
            cifar_classes[label] = [ind]

    per_participant_list = defaultdict(list)
    no_classes = len(cifar_classes.keys())
    class_size = len(cifar_classes[0])
    datasize = {}
    for n in range(no_classes):
        random.shuffle(cifar_classes[n])
        sampled_probabilities = class_size * np.random.dirichlet(
            np.array(no_participants * [alpha]))
        for user in range(no_participants):
            no_imgs = int(round(sampled_probabilities[user]))
            datasize[user, n] = no_imgs
            sampled_list = cifar_classes[n][:min(len(cifar_classes[n]), no_imgs)]
            per_participant_list[user].extend(sampled_list)
            cifar_classes[n] = cifar_classes[n][min(len(cifar_classes[n]), no_imgs):]
    train_img_size = np.zeros(no_participants)
    for i in range(no_participants):
        train_img_size[i] = sum([datasize[i,j] for j in range(10)])
    clas_weight = np.zeros((no_participants,10))
    for i in range(no_participants):
        for j in range(10):
            clas_weight[i,j] = float(datasize[i,j])/float((train_img_size[i]))
    return per_participant_list, clas_weight


if __name__ == '__main__':
    dataset_train = datasets.MNIST('../data/cifar/', train=True, download=True,
                                   transform=transforms.Compose([
                                       transforms.ToTensor(),
                                       transforms.Normalize((0.1307,), (0.3081,))
                                   ]))
    num = 100
    d = cifar_noniid(dataset_train, num)
