# -*- coding: utf-8 -*-
# @Author: Dongqing Sun
# @E-mail: Dongqingsun96@gmail.com
# @Date:   2020-02-23 21:14:12
# @Last Modified by:   Dongqing Sun
# @Last Modified time: 2020-03-03 03:12:38

import os
import argparse as ap
import numpy as np
import scipy.sparse as sp_sparse

from MAESTRO.scATAC_H5Process import *

def scrnaqc_parser(subparsers):
    """
    Add main function init-scatac argument parsers.
    """

    workflow = subparsers.add_parser("scrna-qc", 
        help = "Perform quality control for scRNA-seq gene-cell count matrix.")
    group_input = workflow.add_argument_group("Input files arguments")
    group_input.add_argument("--format", dest = "format", default = "", 
        choices = ["h5", "mtx", "plain"], 
        help = "Format of the count matrix file.")
    group_input.add_argument("--matrix", dest = "matrix", default = "", 
        help = "Location of count matrix file. "
        "If the format is 'h5' or 'plain', users need to specify the name of the count matrix file. "
        "If the format is 'mtx', the 'matrix' should be the name of .mtx formatted matrix file, such as 'matrix.mtx'.")
    group_input.add_argument("--feature", dest = "feature", default = "features.tsv", 
        help = "Location of feature file (required for the format of 'mtx'). "
        "Features correspond to row indices of count matrix. DEFAULT: features.tsv.")
    group_input.add_argument("--gene-column", dest = "gene_column", default = 2, type = int,
        help = "If the format is 'mtx', please specify which column of the feature file to use for gene names. DEFAULT: 2.")
    group_input.add_argument("--barcode", dest = "barcode", default = "barcodes.tsv", 
        help = "Location of barcode file (required for the format of 'mtx'). "
        "Cell barcodes correspond to column indices of count matrix. DEFAULT: barcodes.tsv. ")
    group_input.add_argument("--species", dest = "species", default = "GRCh38", 
        choices = ["GRCh38", "GRCm38"], type = str, 
        help = "Species (GRCh38 for human and GRCm38 for mouse). DEFAULT: GRCh38.")

    # Quality control cutoff
    group_cutoff = workflow.add_argument_group("Quality control arguments")
    group_cutoff.add_argument("--count-cutoff", dest = "count_cutoff", default = 1000, type = int,
        help = "Cutoff for the number of count in each cell. DEFAULT: 1000.")
    group_cutoff.add_argument("--gene-cutoff", dest = "gene_cutoff", default = 500, type = int,
        help = "Cutoff for the number of genes included in each cell. DEFAULT: 500.")        

    group_output = workflow.add_argument_group("Output arguments")
    group_output.add_argument("-d", "--directory", dest = "directory", default = "MAESTRO", 
        help = "Path to the directory where the result file shall be stored. DEFAULT: MAESTRO.")
    group_output.add_argument("--outprefix", dest = "outprefix", default = "10x-genomics", 
        help = "Prefix of output files. DEFAULT: MAESTRO.")



def FilterCell(rawmatrix, feature, barcode, count_cutoff, gene_cutoff, outprefix, species):
    count_per_cell = np.asarray(rawmatrix.sum(axis=0))
    genes_per_cell = np.asarray((rawmatrix > 0).sum(axis=0))
    count_gene = np.concatenate((count_per_cell,genes_per_cell), axis=0)
    statfile = outprefix + "_count_gene_stat.txt"
    with open(statfile, "w") as stat_out:
        header = "Cell\tCount\tGene\n"
        stat_out.write(header)
        for i in range(count_gene.shape[1]):
            stat_list = count_gene[0:2,i].tolist()
            stat_list = [str(int(j)) for j in stat_list]
            stat_out.write(barcode[i] + "\t" + "\t".join(stat_list) + "\n")
    
    passed_cell = np.logical_and(count_per_cell > count_cutoff, genes_per_cell > gene_cutoff)
    gene = [True]*rawmatrix.shape[0]
    passed_cell_matrix = rawmatrix[np.ix_(gene, passed_cell.tolist()[0])]

    passed_barcodes = np.array(barcode)[passed_cell.tolist()[0]].tolist()
    # passed_barcodes = [bc.decode('utf-8') for bc in passed_barcodes]

    write_10X_h5(outprefix + "_filtered_gene_count.h5", matrix = passed_cell_matrix, features = feature, barcodes = passed_barcodes, genome = species, datatype = 'Gene')


def scrna_qc(directory, outprefix, fileformat, matrix, feature, gene_column, barcode, count_cutoff, gene_cutoff, species):

    try:
        os.makedirs(directory)
    except OSError:
        # either directory exists (then we can ignore) or it will fail in the
        # next step.
        pass

    if fileformat == "plain":
        matrix_dict = read_count(matrix)
        rawmatrix = matrix_dict["matrix"]
        rawmatrix = sp_sparse.csc_matrix(rawmatrix, dtype=numpy.float32)
        features = matrix_dict["features"]
        barcodes = matrix_dict["barcodes"]

        if features[0][0] == '"' or features[0][0] == "'":
            features = [i[1:(len(i)-1)] for i in features]
        if barcodes[0][0] == '"' or barcodes[0][0] == "'":
            barcodes = [i[1:(len(i)-1)] for i in barcodes]

        features = [i.split('_')[-1] for i in features]
        barcodes = [i.split('/')[-1].split('.genes.results')[0] for i in barcodes]

    elif fileformat == "h5":
        scrna_count = read_10X_h5(matrix)
        rawmatrix = scrna_count.matrix
        features = scrna_count.names.tolist()
        barcodes = scrna_count.barcodes.tolist()

        if type(features[0]) == bytes:
            features = [i.decode() for i in features]
        if type(barcodes[0]) == bytes:
            barcodes = [i.decode() for i in barcodes]

    elif fileformat == "mtx":
        matrix_dict = read_10X_mtx(matrix_file = matrix, feature_file = feature, barcode_file = barcode, datatype = "Gene", gene_column = gene_column)
        rawmatrix = matrix_dict["matrix"]
        features = matrix_dict["features"]
        barcodes = matrix_dict["barcodes"]

    filename = os.path.join(directory, outprefix)

    FilterCell(rawmatrix = rawmatrix, feature = features, barcode = barcodes, count_cutoff = count_cutoff, gene_cutoff = gene_cutoff, outprefix = filename, species = species)

