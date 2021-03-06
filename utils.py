""" utils.py
"""

import os
import torch
import numpy as np
import torchvision
import torchvision.transforms as transforms
import torchvision.utils as vutils
import time
import warnings
from tensorboardX import *


name_dataparallel = torch.nn.DataParallel.__name__
def lr_warmup(epoch, warmup_length):
    if epoch < warmup_length:
        p = max(0.0, float(epoch)) / float(warmup_length)
        p = 1.0 - p
        return np.exp(-p*p*5.0)
    else:
        return 1.0
    torch.nn.PReLU
    

def load_optimizer(optimizer , model , path , epoch = None ):
    """
    return the epoch
    """
    if type(model).__name__ == name_dataparallel:
        model = model.module

    if epoch is None:
        for i in reversed( range(1000) ):
            p = "{}/{}_epoch{}.pth".format( path,type(optimizer).__name__+'_'+type(model).__name__,i )
            if os.path.exists( p ):
                optimizer.load_state_dict(  torch.load( p ) )
                return i
    else:
        p = "{}/{}_epoch{}.pth".format( path,type(optimizer).__name__+'_'+type(model).__name__,epoch )
        if os.path.exists( p ):
            optimizer.load_state_dict(  torch.load( p )   )
            return epoch
        else:
            warnings.warn("resume optimizer not found at {}".format(p))

    warnings.warn("resume model not found ")
    return -1

def load_model(model,path ,epoch = None , strict= True): 
    """
    return the last epoch
    """
    if type(model).__name__ == name_dataparallel:
        model = model.module
    if epoch is None:
        for i in reversed( range(1000) ):
            p = "{}/{}_epoch{}.pth".format( path,type(model).__name__,i )
            if os.path.exists( p ):
                model.load_state_dict(  torch.load( p ) , strict = strict)
                return i
    else:
        p = "{}/{}_epoch{}.pth".format( path,type(model).__name__,epoch )
        if os.path.exists( p ):
            model.load_state_dict(  torch.load( p ) , strict = strict)
            return epoch
        else:
            warnings.warn("resume model not found at {}".format(p))

    warnings.warn("resume model not found ")
    return -1

    
def set_requires_grad(module , b ):
    for parm in module.parameters():
        parm.requires_grad = b

def adjust_dyn_range(x, drange_in, drange_out):
    if not drange_in == drange_out:
        scale = float(drange_out[1]-drange_out[0])/float(drange_in[1]-drange_in[0])
        bias = drange_out[0]-drange_in[0]*scale
        x = x.mul(scale).add(bias)
    return x


def resize(x, size):
    transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Scale(size),
        transforms.ToTensor(),
        ])
    return transform(x)


def make_image_grid(x, ngrid):
    x = x.clone().cpu()
    if pow(ngrid,2) < x.size(0):
        grid = make_grid(x[:ngrid*ngrid], nrow=ngrid, padding=0, normalize=True, scale_each=False)
    else:
        grid = torch.FloatTensor(ngrid*ngrid, x.size(1), x.size(2), x.size(3)).fill_(1)
        grid[:x.size(0)].copy_(x)
        grid = make_grid(grid, nrow=ngrid, padding=0, normalize=True, scale_each=False)
    return grid


def save_image_single(x, path, imsize=512):
    from PIL import Image
    grid = make_image_grid(x, 1)
    ndarr = grid.mul(255).clamp(0, 255).byte().permute(1, 2, 0).numpy()
    im = Image.fromarray(ndarr)
    im = im.resize((imsize,imsize), Image.NEAREST)
    im.save(path)


def save_image_grid(x, path, imsize=512, ngrid=4):
    from PIL import Image
    grid = make_image_grid(x, ngrid)
    ndarr = grid.mul(255).clamp(0, 255).byte().permute(1, 2, 0).numpy()
    im = Image.fromarray(ndarr)
    im = im.resize((imsize,imsize), Image.NEAREST)
    im.save(path)


def save_model(model,dirname,epoch):
    if type(model).__name__ == name_dataparallel:
        model = model.module
    torch.save( model.state_dict() , '{}/{}_epoch{}.pth'.format(dirname,type(model).__name__,epoch ) )
def save_optimizer(optimizer,model,dirname,epoch):
    if type(model).__name__ == name_dataparallel:
        model = model.module
    torch.save( optimizer.state_dict() , '{}/{}_epoch{}.pth'.format(dirname,type(optimizer).__name__ +'_' +type(model).__name__,epoch ) )

def make_summary(writer, key, value, step):
    if hasattr(value, '__len__'):
        for idx, img in enumerate(value):
            summary = tf.Summary()
            sio = BytesIO()
            scipy.misc.toimage(img).save(sio, format='png')
            image_summary = tf.Summary.Image(encoded_image_string=sio.getvalue())
            summary.value.add(tag="{}/{}".format(key, idx), image=image_summary)
            writer.add_summary(summary, global_step=step)
    else:
        summary = tf.Summary(value=[tf.Summary.Value(tag=key, simple_value=value)])
        writer.add_summary(summary, global_step=step)




import torch
import math
irange = range
def make_grid(tensor, nrow=8, padding=2,
              normalize=False, range=None, scale_each=False, pad_value=0):
    """Make a grid of images.
    Args:
        tensor (Tensor or list): 4D mini-batch Tensor of shape (B x C x H x W)
            or a list of images all of the same size.
        nrow (int, optional): Number of images displayed in each row of the grid.
            The Final grid size is (B / nrow, nrow). Default is 8.
        padding (int, optional): amount of padding. Default is 2.
        normalize (bool, optional): If True, shift the image to the range (0, 1),
            by subtracting the minimum and dividing by the maximum pixel value.
        range (tuple, optional): tuple (min, max) where min and max are numbers,
            then these numbers are used to normalize the image. By default, min and max
            are computed from the tensor.
        scale_each (bool, optional): If True, scale each image in the batch of
            images separately rather than the (min, max) over all images.
        pad_value (float, optional): Value for the padded pixels.
    Example:
        See this notebook `here <https://gist.github.com/anonymous/bf16430f7750c023141c562f3e9f2a91>`_
    """
    if not (torch.is_tensor(tensor) or
            (isinstance(tensor, list) and all(torch.is_tensor(t) for t in tensor))):
        raise TypeError('tensor or list of tensors expected, got {}'.format(type(tensor)))

    # if list of tensors, convert to a 4D mini-batch Tensor
    if isinstance(tensor, list):
        tensor = torch.stack(tensor, dim=0)

    if tensor.dim() == 2:  # single image H x W
        tensor = tensor.view(1, tensor.size(0), tensor.size(1))
    if tensor.dim() == 3:  # single image
        if tensor.size(0) == 1:  # if single-channel, convert to 3-channel
            tensor = torch.cat((tensor, tensor, tensor), 0)
        return tensor
    if tensor.dim() == 4 and tensor.size(1) == 1:  # single-channel images
        tensor = torch.cat((tensor, tensor, tensor), 1)

    if normalize is True:
        tensor = tensor.clone()  # avoid modifying tensor in-place
        if range is not None:
            assert isinstance(range, tuple), \
                "range has to be a tuple (min, max) if specified. min and max are numbers"

        def norm_ip(img, min, max):
            img.clamp_(min=min, max=max)
            img.add_(-min).div_(max - min)

        def norm_range(t, range):
            if range is not None:
                norm_ip(t, range[0], range[1])
            else:
                norm_ip(t, t.min(), t.max())

        if scale_each is True:
            for t in tensor:  # loop over mini-batch dimension
                norm_range(t, range)
        else:
            norm_range(tensor, range)

    # make the mini-batch of images into a grid
    nmaps = tensor.size(0)
    xmaps = min(nrow, nmaps)
    ymaps = int(math.ceil(float(nmaps) / xmaps))
    height, width = int(tensor.size(2) + padding), int(tensor.size(3) + padding)
    grid = tensor.new(3, height * ymaps + padding, width * xmaps + padding).fill_(pad_value)
    k = 0
    for y in irange(ymaps):
        for x in irange(xmaps):
            if k >= nmaps:
                break
            grid.narrow(1, y * height + padding, height - padding)\
                .narrow(2, x * width + padding, width - padding)\
                .copy_(tensor[k])
            k = k + 1
    return grid


def save_image(tensor, filename, nrow=8, padding=2,
               normalize=False, range=None, scale_each=False, pad_value=0):
    """Save a given Tensor into an image file.
    Args:
        tensor (Tensor or list): Image to be saved. If given a mini-batch tensor,
            saves the tensor as a grid of images by calling ``make_grid``.
        **kwargs: Other arguments are documented in ``make_grid``.
    """
    from PIL import Image
    tensor = tensor.cpu()
    grid = make_grid(tensor, nrow=nrow, padding=padding, pad_value=pad_value,
                     normalize=normalize, range=range, scale_each=scale_each)
    ndarr = grid.mul(255).clamp(0, 255).byte().permute(1, 2, 0).numpy()
    im = Image.fromarray(ndarr)
    im.save(filename)

class LRmanager :
    def __init__(self,optimizer,boundaries,lr,decay):
        self.boundaries=boundaries
        self.lr=lr
        self.decay=decay
        self.optimizer=optimizer

    def get(self,n):
        _lr=self.lr*self.decay**(sum(n>np.array(self.boundaries)))
        for param_group in self.optimizer.param_groups:
            param_group['lr']=_lr*param_group['lr_mult']
            param_group['weight_decay']=self.decay*param_group['decay_mult']
def accuracy(output, target, topk=(1,)):
    """Computes the precision@k for the specified values of k"""
    maxk = max(topk)
    batch_size = target.size(0)

    _, pred = output.topk(maxk, 1, True, True)
    pred = pred.t()
    correct = pred.eq(target.view(1, -1).expand_as(pred))

    res = []
    for k in topk:
        correct_k = correct[:k].view(-1).float().sum(0)
        res.append(correct_k.mul_(100.0 / batch_size))
    return res


class Writer():
    def __init__(self,path):
        self.writer=SummaryWriter(log_dir=path)
        self.method={
                'scalar':self.writer.add_scalar,
                'image':self.writer.add_image,
                'histogram':self.writer.add_histogram,
                'graph':self.writer.add_graph
                }
    def __call__(self,name,global_step,category,value):
        if category in self.method:
            self.method[category](name,value,global_step)
        else:
            raise KeyError( '{} not support'.format(category) )
    def write(self):
        self.writer.close()

def weight_init(m):
    if isinstance(m,torch.nn.Conv2d):
        torch.nn.init.xavier_normal_(m.weight.data)
        torch.nn.init.constant_(m.bias.data,0)
    if isinstance(m,torch.nn.Linear):
        torch.nn.init.xavier_normal_(m.weight.data)
        torch.nn.init.constant_(m.bias.data,0)



