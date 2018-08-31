#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright © 2017 Michael J. Hayford
""" Support for the Hoya Glass catalog

Created on Wed Aug  2 10:11:18 2017

@author: Michael J. Hayford
"""
import logging
from pathlib import Path

from math import sqrt
import xlrd
import numpy as np

from . import glasserror as ge


class HoyaCatalog:
    xl_data = None
    data_header = 1
    data_start = 4
    num_glasses = 191
    name_col_offset = 2
    coef_col_offset = 28
    index_col_offset = 10

    def __init__(self):
        # Open the workbook
        path = Path(__file__).resolve().parent
        fname = 'HOYA20171226.xlsx'
        xl_workbook = xlrd.open_workbook(path/fname)
        self.xl_data = xl_workbook.sheet_by_index(0)
        self.name_col_offset = self.xl_data.row_values(0, 0).index('Glass\u3000Type')
        gnames = self.xl_data.col_values(self.name_col_offset, self.data_start)
        while gnames and len(gnames[-1]) is 0:
            gnames.pop()
        self.num_glasses = len(gnames)
        colnames = self.xl_data.row_values(self.data_header, 0)
        self.coef_col_offset = colnames.index('A0')
        self.index_col_offset = colnames.index('n1529.6')

    def glass_index(self, gname):
        gnames = self.xl_data.col_values(self.name_col_offset, self.data_start)
        if gname in gnames:
            gindex = gnames.index(gname)
        else:
            logging.info('Hoya glass %s not found', gname)
            raise ge.GlassNotFoundError("Hoya", gname)

        return gindex

    def data_index(self, dname):
        if dname in self.xl_data.row_values(self.data_header, 0):
            dindex = self.xl_data.row_values(self.data_header, 0).index(dname)
        else:
            logging.info('Hoya glass data type %s not found', dname)
            raise ge.GlassDataNotFoundError("Hoya", dname)

        return dindex

    def glass_data(self, row):
        return self.xl_data.row_values(self.data_start+row, 0)

    def catalog_data(self, col):
        return self.xl_data.col_values(col, self.data_start,
                                       self.data_start+self.num_glasses)

    def glass_coefs(self, gindex):
        c = (self.xl_data.row_values(self.data_start+gindex,
                                     self.coef_col_offset,
                                     self.coef_col_offset+12))
        return [x*10**y for x, y in zip(c[::2], c[1::2])]

    def glass_map_data(self, wvl='d'):
        if wvl == 'd':
            nd = np.array(self.catalog_data(self.data_index('nd')))
            nF = np.array(self.catalog_data(self.data_index('nF')))
            nC = np.array(self.catalog_data(self.data_index('nC')))
            dFC = nF-nC
            vd = (nd - 1.0)/dFC
            PCd = (nd-nC)/dFC
            names = self.catalog_data(self.name_col_offset)
            return nd, vd, PCd, names
        elif wvl == 'e':
            ne = np.array(self.catalog_data(self.data_index('ne')))
            nF = np.array(self.catalog_data(self.data_index('nF')))
            nC = np.array(self.catalog_data(self.data_index('nC')))
            dFC = nF-nC
            ve = (ne - 1.0)/dFC
            PCe = (ne-nC)/dFC
            names = self.catalog_data(self.name_col_offset)
            return ne, ve, PCe, names
        else:
            return None


class HoyaGlass:
    catalog = HoyaCatalog()

    def __init__(self, gname):
        self.gindex = self.catalog.glass_index(gname)

    def __repr__(self):
        return 'Hoya ' + self.name() + ': ' + self.glass_code()

    def glass_code(self):
        nd = self.glass_item('nd')
        vd = self.glass_item('νd')
        return str(1000*round((nd - 1), 3) + round(vd/100, 3))

    def glass_data(self):
        return self.catalog.glass_data(self.gindex)

    def name(self):
        return self.catalog.xl_data.cell_value(self.catalog.data_start+self.gindex,
                                               self.catalog.name_col_offset)

    def glass_item(self, dname):
        dindex = self.catalog.data_index(dname)
        if dindex is None:
            return None
        else:
            return self.glass_data()[dindex]

    def rindex(self, wv_nm):
        wv = 0.001*wv_nm
        wv2 = wv*wv
        coefs = self.catalog.glass_coefs(self.gindex)
        n2 = coefs[0] + coefs[1]*wv2
        wvm2 = 1/wv2
        n2 = n2 + wvm2*(coefs[2] + wvm2*(coefs[3]
                        + wvm2*(coefs[4] + wvm2*coefs[5])))
        return sqrt(n2)
