'''
The following is a class the allows one to utilize a stateful lstm model in pytorch
This allows for the reset state to be a hyperparameter in which you can learn the most generalizable model based on how long the recurrency analysis should be
PARAMETERS
NEED TO MAKE PADDING AVAILABLE
'''

import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
import math

class StatefulConv2dLSTMCell(nn.Module):
    def __init__(self, input_shape, no_filters, kernel_shape, strides, pad=0, weight_init=None, reccurent_weight_init=None,  cell_weight_init=None, bias_init=None, drop=None, rec_drop=None):
        super(StatefulConv2dLSTMCell, self).__init__()

        # if(weight_init==None):
        #     #weights need to be the shape of input or x and the output
        #     self.W_f = nn.Parameter(torch.zeros(kernel_shape[0], kernel_shape[1], int(input_shape[-1]), no_filters))
        #     self.W_f = nn.init.xavier_normal(self.W_f)
        #     self.W_i = nn.Parameter(torch.zeros(kernel_shape[0], kernel_shape[1], int(input_shape[-1]), no_filters))
        #     self.W_i = nn.init.xavier_normal(self.W_i)
        #     self.W_o = nn.Parameter(torch.zeros(kernel_shape[0], kernel_shape[1], int(input_shape[-1]), no_filters))
        #     self.W_o = nn.init.xavier_normal(self.W_o)
        #     self.W_c = nn.Parameter(torch.zeros(kernel_shape[0], kernel_shape[1], int(input_shape[-1]), no_filters))
        #     self.W_c = nn.init.xavier_normal(self.W_c)
        # else:
        #     self.W_f = nn.Parameter(torch.zeros(kernel_shape[0], kernel_shape[1], int(input_shape[-1]), no_filters))
        #     self.W_f = weight_init(self.W_f)
        #     self.W_i = nn.Parameter(torch.zeros(kernel_shape[0], kernel_shape[1], int(input_shape[-1]), no_filters))
        #     self.W_i = weight_init(self.W_i)
        #     self.W_o = nn.Parameter(torch.zeros(kernel_shape[0], kernel_shape[1], int(input_shape[-1]), no_filters))
        #     self.W_o = weight_init(self.W_o)
        #     self.W_c = nn.Parameter(torch.zeros(kernel_shape[0], kernel_shape[1], int(input_shape[-1]), no_filters))
        #     self.W_c = weight_init(self.W_c)
        #
        # if(reccurent_weight_init == None):
        #     #Weight matrices for hidden state
        #     self.U_f = nn.Parameter(torch.zeros(kernel_shape[0], kernel_shape[1], no_filters, no_filters))
        #     self.U_f = nn.init.xavier_normal(self.U_f)
        #     self.U_i = nn.Parameter(torch.zeros(kernel_shape[0], kernel_shape[1], no_filters, no_filters))
        #     self.U_i = nn.init.xavier_normal(self.U_i)
        #     self.U_o = nn.Parameter(torch.zeros(kernel_shape[0], kernel_shape[1], no_filters, no_filters))
        #     self.U_o = nn.init.xavier_normal(self.U_o)
        #     self.U_c = nn.Parameter(torch.zeros(kernel_shape[0], kernel_shape[1], no_filters, no_filters))
        #     self.U_c = nn.init.xavier_normal(self.U_c)
        # else:
        #     self.U_f = nn.Parameter(torch.zeros(kernel_shape[0], kernel_shape[1], no_filters, no_filters))
        #     self.U_f = recurrent_weight_initializer(self.U_f)
        #     self.U_i = nn.Parameter(torch.zeros(kernel_shape[0], kernel_shape[1], no_filters, no_filters))
        #     self.U_i = recurrent_weight_initializer(self.U_i)
        #     self.U_o = nn.Parameter(torch.zeros(kernel_shape[0], kernel_shape[1], no_filters, no_filters))
        #     self.U_o = recurrent_weight_initializer(self.U_o)
        #     self.U_c = nn.Parameter(torch.zeros(kernel_shape[0], kernel_shape[1], no_filters, no_filters))
        #     self.U_c = recurrent_weight_initializer(self.U_c)

        #This needs to be different depending on padding
        if(cell_weight_init == None):
            #Weight matrices for hidden state
            # tup = (int(int(input_shape[1] - kernel_shape[0] + 1) / strides), int( int(input_shape[2] - kernel_shape[1] + 1) / strides), no_filters)
            self.V_f = nn.Parameter(torch.zeros(
                no_filters, int(int(math.ceil((input_shape[1] - kernel_shape[0] + 1) / (strides)))), int( math.ceil((input_shape[2] - kernel_shape[1] + 1) / strides))))
            self.V_f = nn.init.xavier_normal(self.V_f)
            self.V_i = nn.Parameter(torch.zeros(
                no_filters, int( int(math.ceil((input_shape[1] - kernel_shape[0] + 1) / (strides)))), int( math.ceil((input_shape[2] - kernel_shape[1] + 1) / strides))))
            self.V_i = nn.init.xavier_normal(self.V_i)
            self.V_o = nn.Parameter(torch.zeros(
                no_filters, int( int(math.ceil((input_shape[1] - kernel_shape[0] + 1) / (strides)))), int( math.ceil((input_shape[2] - kernel_shape[1] + 1) / strides))))
            self.V_o = nn.init.xavier_normal(self.V_o)
        else:
            self.V_f = nn.Parameter(torch.zeros(
                int( int(input_shape[1] - kernel_shape[0] + 1) / strides), int( int(input_shape[2] - kernel_shape[1] + 1) / strides), no_filters))
            self.V_f = nn.init.xavier_normal(self.V_f)
            self.V_i = nn.Parameter(torch.zeros(
                int( int(input_shape[1] - kernel_shape[0] + 1) / strides), int( int(input_shape[2] - kernel_shape[1] + 1) / strides), no_filters))
            self.V_i = nn.init.xavier_normal(self.V_i)
            self.V_o = nn.Parameter(torch.zeros(
                int( int(input_shape[1] - kernel_shape[0] + 1) / strides), int( int(input_shape[2] - kernel_shape[1] + 1) / strides), no_filters))
            self.V_o = nn.init.xavier_normal(self.V_o)

        if(bias_init==None):
            #bias initialized to zeros
            self.b_f = nn.Parameter(torch.zeros(no_filters))
            self.b_i = nn.Parameter(torch.zeros(no_filters))
            self.b_o = nn.Parameter(torch.zeros(no_filters))
            self.b_c = nn.Parameter(torch.zeros(no_filters))
        else:
            self.b_f = bias_init(torch.zeros(no_filters))
            self.b_i = bias_init(torch.zeros(no_filters))
            self.b_o = bias_init(torch.zeros(no_filters))
            self.b_c = bias_init(torch.zeros(no_filters))

        self.stride = strides
        self.kernel = kernel_shape
        self.no_filters = no_filters
        self.inp_shape = input_shape

        #for now no padding

        self.conv2d_x_f = nn.Conv2d(input_shape[0], no_filters, kernel_shape, stride=strides, padding=pad)
        self.conv2d_x_i = nn.Conv2d(input_shape[0], no_filters, kernel_shape, stride=strides, padding=pad)
        self.conv2d_x_o = nn.Conv2d(input_shape[0], no_filters, kernel_shape, stride=strides, padding=pad)
        self.conv2d_x_c = nn.Conv2d(input_shape[0], no_filters, kernel_shape, stride=strides, padding=pad)
        self.conv2d_h_f = nn.Conv2d(no_filters, no_filters, kernel_shape, padding=2)
        self.conv2d_h_i = nn.Conv2d(no_filters, no_filters, kernel_shape, padding=2)
        self.conv2d_h_o = nn.Conv2d(no_filters, no_filters, kernel_shape, padding=2)
        self.conv2d_h_c = nn.Conv2d(no_filters, no_filters, kernel_shape, padding=2)

        self.output_shape = self.V_o.size()
        if(drop==None):
            self.dropout = nn.Dropout(0)
        else:
            self.dropout = nn.Dropout(drop)
        if(rec_drop == None):
            self.rec_dropout = nn.Dropout(0)
        else:
            self.rec_dropout = nn.Dropout(drop)

    def forward(self, X_t, previous_hidden_memory_tuple):
        h_t_previous, c_t_previous = previous_hidden_memory_tuple[0], previous_hidden_memory_tuple[1]

        X_t = self.dropout(X_t)
        h_t_previous = self.rec_dropout(h_t_previous)
        c_t_previous = self.rec_dropout(c_t_previous)

        f_t = F.sigmoid(
            self.conv2d_x_f(X_t) + self.conv2d_h_f(h_t_previous) + c_t_previous * self.V_f  #w_f needs to be the previous input shape by the number of hidden neurons
        )
        #i(t) = sigmoid(W_i (conv) x(t) + U_i (conv) h(t-1) + V_i (*) c(t-1)  + b_i)
        i_t = F.sigmoid(
            self.conv2d_x_i(X_t) + self.conv2d_h_i(h_t_previous) + c_t_previous * self.V_i
        )
        #o(t) = sigmoid(W_o (conv) x(t) + U_o (conv) h(t-1) + V_i (*) c(t-1) + b_o)
        o_t = F.sigmoid(
            self.conv2d_x_o(X_t) + self.conv2d_h_o(h_t_previous) + c_t_previous * self.V_o
        )
        #c(t) = f(t) (*) c(t-1) + i(t) (*) hypertan(W_c (conv) x_t + U_c (conv) h(t-1) + b_c)
        c_hat_t = F.tanh(
            self.conv2d_x_c(X_t) + self.conv2d_h_c(h_t_previous)
        )
        c_t = (f_t * c_t_previous) + (i_t * c_hat_t)
        #h_t = o_t * tanh(c_t)
        h_t = o_t * F.tanh(c_t)
        #h(t) = o(t) (*) hypertan(c(t))

        return h_t, c_t

#I prefer hard sigmoid for gradient passing this was my tensorflow way of doing it
# def hard_sigmoid(x):
#     """hard sigmoid for convlstm"""
#     x = (0.2 * x) + 0.5
#     zero = tf.convert_to_tensor(0., x.dtype.base_dtype)
#     one = tf.convert_to_tensor(1., x.dtype.base_dtype)
#     x = tf.clip_by_value(x, zero, one)
#     return x


'''
torch.nn.self.conv2d(in_channels, out_channels, kernel_size, stride=1, padding=0, dilation=1, groups=1, bias=True)
'''
