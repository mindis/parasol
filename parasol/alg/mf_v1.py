# blocked matrix factorization using stochastic gradient 

import sys
import json
import numpy as np
from mpi4py import MPI
import random
from time import clock
from optparse import OptionParser
from parasol.decomp import npfact2d, npfactx
from parasol.writer.writer import outputvec    
from parasol.ps import paralg
    
class mf(paralg):

    def __init__(self, comm, hosts_dict_lst, nworker, k, input_filename, outp, outq, alpha = 0.002, beta = 0.02, rounds = 3, limit_s = 3):
        paralg.__init__(self, comm, hosts_dict_lst, nworker, rounds, limit_s)
        self.rank = self.comm.Get_rank()
        self.a, self.b = npfact2d(nworker)
        #self.a, self.b = npfactx(nworker)
	self.k = k
	#print 'deubs', self.k
        self.filename = input_filename
        self.outp = outp
        self.outq = outq
        
        self.alpha = alpha
        self.beta = beta
        self.rounds = rounds
        
        # create folder
        paralg.crt_outfolder(self, self.outp)
        paralg.crt_outfolder(self, self.outq)
        self.comm.barrier()
    
    def __mf_kernel(self):#, alpha = 0.0002, beta = 0.02, rounds = 5):
        import time
	pl_sz = self.p.shape[0]
        ql_sz = self.q.shape[1]
        print 'data size is', len(self.graph)
        delta_p = np.random.rand(pl_sz, self.k)
        delta_q = np.random.rand(self.k, ql_sz)
	print 'ffffffff', self.a, self.b
	for it in xrange(self.rounds):
            print 'round', it, self.rank
	    for index in xrange(pl_sz):
	        key = 'p[' + str(index) + ',:]_' + str(self.rank / self.b)
	        self.p[index, :] = paralg.paralg_read(self, key)
	    for index in xrange(ql_sz):
	        key = 'q[:,' + str(index) + ']_' + str(self.rank % self.b)
	        self.q[:, index] = paralg.paralg_read(self, key)
            print 'after round pull', self.rank
            
            #start = clock()
            random.shuffle(self.graph)
            #end = cl ck()
            #print 'shuffle time is', end - start
            
	    for i in xrange(delta_p.shape[0]):
	        for j in xrange(delta_p.shape[1]):
		    delta_p[i][j] = self.p[i][j]
	    for i in xrange(delta_q.shape[0]):
	        for j in xrange(delta_q.shape[1]):
		    delta_q[i][j] = self.q[i][j]

            for i, j, v in self.graph:
	        eij = v - np.dot(self.p[i, :], self.q[:, j])
		#delta_p = []
		#delta_q = []
                #for ki in xrange(self.k):
                #    delta_p.append(self.alpha * (2 * eij * self.q[ki][j] - self.beta * self.p[i][ki]))
                #    self.p[i][ki] += delta_p[ki]
                #    delta_q.append(self.alpha * (2 * eij * self.p[i][ki] - self.beta * self.q[ki][j]))
		#    self.q[ki][j] += delta_q[ki]
	        tmpp = self.alpha * (2 * eij * self.q[:, j] - self.beta * self.p[i, :])
		tmpq = self.alpha * (2 * eij * self.p[i, :] - self.beta * self.q[:, j])
		self.p[i, :] += tmpp
		self.q[:, j] += tmpq

	    for index in xrange(pl_sz):
	        key = 'p[' + str(index) + ',:]_' + str(self.rank / self.b)
		#print 'rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrank:', self.rank, 'key', key 
	        paralg.paralg_inc(self, key, (self.p[index, :] - delta_p[index, :]) / self.b)
	    for index in xrange(ql_sz):
	        key = 'q[:,' + str(index) + ']_' + str(self.rank % self.b)
		#print 'sssssssssssssssssssssssssssssssssssssssssank:', self.rank, 'key', key 
                paralg.paralg_inc(self, key, (self.q[:, index] - delta_q[: ,index]) / self.a)
	    
	    #start = clock()
            #print 'local calc time is', start - end
	    paralg.iter_done(self)
    
        # last pull p, may not calc on this procs, but can be calced on others
        self.comm.barrier()
        start = clock()
	for index in xrange(pl_sz):
	    key = 'p[' + str(index) + ',:]_' + str(self.rank / self.b)
	    self.p[index, :] = paralg.paralg_read(self, key)
	for index in xrange(ql_sz):
	    key = 'q[:,' + str(index) + ']_' + str(self.rank % self.b)
	    self.q[:, index] = paralg.paralg_read(self, key)
	self.comm.barrier()
        #end = clock()
        #print 'last pull time is', end - start
        self.q = self.q.transpose()
        
    def __matrix_factorization(self):
        dimx = self.dimx
	dimy = self.dimy
        self.p = np.random.rand(dimx, self.k)
        self.q = np.random.rand(self.k, dimy)
	#self.p = np.array([[0.46500647, 0.10950494],
	#		[0.47867466, 0.49807307],
	#		[0.33376554, 0.24195584],
	#   		[0.9739632, 0.37057525],
	#    		[0.64395383, 0.30542925]])
	#if self.rank == 0:
	#    self.p = np.array([[0.46500647, 0.10950494],[0.47867466, 0.49807307],[0.33376554, 0.24195584]])
	#if self.rank == 1:
	#    self.p = np.array([[0.9739632, 0.37057525], [0.64395383, 0.30542925]])
	#self.q = np.array([[0.96802557, 0.22467435, 0.49266987, 0.18327164],
	#		[0.81976892, 0.57031032, 0.22665017, 0.23747223]])
	#print self.p
	#print self.q
        #print 'dimx is', dimx
        #print 'dimy is', dimy
        #print 'before init push'
        # init push dimx and dimy
	for index in xrange(dimx):
	    key = 'p[' + str(index) + ',:]_' + str(self.rank / self.b)
	    paralg.paralg_write(self, key, self.p[index, :])
	for index in xrange(dimy):
	    key = 'q[:,' + str(index) + ']_' + str(self.rank % self.b)
	    paralg.paralg_write(self, key, self.q[:, index])
        #print 'finish init push'
        self.comm.barrier()
        
	# kernel mf solver
        self.__mf_kernel()
        
	self.comm.barrier()

    def solve(self):
        import time
        from parasol.utils.lineparser import parser_b
        #from parasol.utils.lineparser import parser_ussrt
	paralg.loadinput(self, self.filename, parser_b(','), 'fsmap')
        self.comm.barrier()
        s = time.time()
	self.__matrix_factorization()
        f = time.time()
	print 'rank ', self.rank, ' kernel time ', f - s
	self.comm.barrier()
    
    def tricky(self, r):
        import math
	fm = math.floor(r)
	if (r - fm) > 0.666:
	    return fm + 1.
	elif (r - fm) < 0.333:
	    return fm
	else:
	    return r

    def __calc_esum(self):
        esum = 0.
        q = self.q.transpose()
        for i, j, v in self.graph:
	    tmp = np.dot(self.p[i, :], q[:, j])
            #esum += (v - self.tricky(tmp)) ** 2
	    esum += (v - tmp) ** 2
	    #print v
	    #print np.dot(self.p[i, :], q[:, j])
	#print self.graph
	#print np.dot(self.p, self.q.T)
	#print self.rmap
	#print self.cmap
	#print self.dmap
	#print self.col_dmap
        return esum
    
    def calc_rmse(self):
        import math
        esum = self.__calc_esum()
        self.comm.barrier()
	print 'esum', esum
        esum = self.comm.allreduce(esum, op = MPI.SUM)
	cnt = self.comm.allreduce(len(self.graph), op = MPI.SUM)
	print 'esum after', esum
	print cnt
        return math.sqrt(esum / cnt)
         
    def write_mf_result(self):
        if self.rank % self.b == 0:
            outputvec(self.outp, self.rmap, self.p, self.k, self.comm, self.suffix)
        if self.rank < self.b:
            outputvec(self.outq, self.cmap, self.q, self.k, self.comm, self.suffix)