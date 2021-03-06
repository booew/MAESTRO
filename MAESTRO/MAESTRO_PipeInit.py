# -*- coding: utf-8 -*-
# @Author: Dongqing Sun
# @E-mail: Dongqingsun96@gmail.com
# @Date:   2020-02-23 19:40:27
# @Last Modified by:   Dongqing Sun
# @Last Modified time: 2020-03-04 01:20:52


import os
import shutil
import argparse as ap
from jinja2 import Template
from pkg_resources import resource_filename

def scatac_parser(subparsers):
    """
    Add main function init-scatac argument parsers.
    """

    workflow = subparsers.add_parser("scatac-init", help = "Initialize the MAESTRO scATAC-seq workflow in a given directory. "
        "This will install a Snakefile and a config file in this directory. "
        "You can configure the config file according to your needs, and run the workflow with Snakemake "
        "(https://bitbucket.org/johanneskoester/snakemake).")

    # Input files arguments
    group_input = workflow.add_argument_group("Input files arguments")
    group_input.add_argument("--platform", dest = "platform", default = "10x-genomics", 
        choices = ["10x-genomics", "sci-ATAC-seq", "microfluidic"], 
        help = "Platform of single cell ATAC-seq. DEFAULT: 10x-genomics.")
    group_input.add_argument("--fastq-dir", dest = "fastq_dir", type = str, default = "", 
        help = "Directory where fastq files are stored.")
    group_input.add_argument("--fastq-prefix", dest = "fastq_prefix", type = str, default = "", 
        help = "Sample name of fastq file (required for the platform of '10x-genomics' or 'sci-ATAC-seq'). "
        "When the platform is '10x-genomics', if there is a file named pbmc_1k_v2_S1_L001_I1_001.fastq.gz, the prefix is 'pbmc_1k_v2'."
        "If the platform is 'sci-ATAC-seq', there are two ways to provide fastq files. "
        "The first is to provide pair-end sequencing results which contain two fastq files -- prefix_1.fastq and prefix_2.fastq. "
        "If in this way, the barcode for each read needs to be included in the reads ID (the first line of each read) "
        "in the format of '@ReadName:CellBarcode:OtherInformation'. For example, @rd.1:TCTCCCGCCGAGGCTGACTGCATAAGGCGAAT:SHEN-MISEQ02:1:1101:15311:1341. "
        "The other way is to provide 10x-like fastq files which should contain three fastq files -- prefix_R1.fastq, prefix_R2.fastq and prefix_R3.fastq. "
        "In this way, read1, barcode and read2 are associated with R1, R2, R3, respectively.")
    group_input.add_argument("--species", dest = "species", default = "GRCh38",
        choices = ["GRCh38", "GRCm38"], type = str, 
        help = "Species (GRCh38 for human and GRCm38 for mouse). DEFAULT: GRCh38.")

    # Output arguments
    group_output = workflow.add_argument_group("Output arguments")
    group_output.add_argument("--cores", dest = "cores", default = 8, 
        type = int, help = "Number of cores to use. DEFAULT: 8.")
    group_output.add_argument("-d", "--directory", dest = "directory", type = str, default = "MAESTRO", 
        help = "Path to the directory where the workflow shall be initialized and results shall be stored. DEFAULT: MAESTRO.")
    group_output.add_argument("--outprefix", dest = "outprefix", type = str, default = "MAESTRO", 
        help = "Prefix of output files. DEFAULT: MAESTRO.")

    # Quality control cutoff
    group_cutoff = workflow.add_argument_group("Quality control arguments")
    group_cutoff.add_argument("--count-cutoff", dest = "count_cutoff", default = 1000, type = int, 
        help = "Cutoff for the number of count in each cell. DEFAULT: 1000.")
    group_cutoff.add_argument("--frip-cutoff", dest = "frip_cutoff", default = 0.2, type = float, 
        help = "Cutoff for fraction of reads in promoter in each cell. DEFAULT: 0.2.")

    # Reference genome arguments
    group_reference = workflow.add_argument_group("Reference genome arguments")
    group_reference.add_argument("--giggleannotation", dest = "giggleannotation", 
        default = "/home1/wangchenfei/Project/SingleCell/scATAC/Code/MAESTRO/MAESTRO/annotations/giggle", 
        help = "Path of the giggle annotation file required for regulator identification. "
        "Please download the annotation file from "
        "http://cistrome.org/~chenfei/MAESTRO/giggle.tar.gz and decompress it.")
    group_reference.add_argument("--fasta", dest = "fasta", 
        default = "/home1/wangchenfei/annotations/refdata-cellranger-atac-GRCh38-1.1.0/fasta/genome.fa", 
        help = "Genome fasta file for BWA. If the platform is not '10x-genomics', please specify it. "
        "Users can just use the genome.fa file in the reference required for Cell Ranger ATAC."
        "For example, 'refdata-cellranger-atac-GRCh38-1.1.0/fasta/genome.fa'.")
    # group_reference.add_argument("--cellranger", dest = "cellranger", 
    #     default = "/home1/wangchenfei/annotations/refdata-cellranger-atac-GRCh38-1.1.0", 
    #     help = "Genome annotation file downloaded from 10x-genomics "
    #     "(https://support.10xgenomics.com/single-cell-atac/software/downloads/latest) "
    #     "required for Cell Ranger ATAC. ")

    # Barcode library arguments
    group_barcode = workflow.add_argument_group("Barcode library arguments, only for platform of 'sci-ATAC-seq'")
    group_barcode.add_argument("--whitelist", dest = "whitelist", type = str, 
        default = "",
        help = "If the platform is 'sci-ATAC-seq' or '10x-genomics', please specify the barcode library (whitelist) "
        "so that the pipeline can correct cell barcodes with 1 base mismatched. "
        "Otherwise, the pipeline will automatically output the barcodes with enough read count (>1000)."
        "The 10X Chromium whitelist file can be found inside the CellRanger-ATAC distribution. "
        "For example, in CellRanger-ATAC 1.1.0, the whitelist is "
        "'cellranger-atac-1.1.0/cellranger-atac-cs/1.1.0/lib/python/barcodes/737K-cratac-v1.txt'. ")

    # Customized peak arguments
    group_peak = workflow.add_argument_group("Customized peak arguments")
    group_peak.add_argument("--custompeak", dest = "custompeak", action = "store_true", 
        help = "Whether or not to provide custom peaks. If set, users need to provide "
        "the file location of peak file through '--custompeak-file' and then MAESTRO will merge "
        "the custom peak file and the peak file called from all fragments using MACS2. "
        "By default (not set), the pipeline will use the peaks called using MACS2.")
    group_peak.add_argument("--custompeak-file", dest = "custompeak_file", type = str, default = "", 
        help = "If '--custompeak' is set, please provide the file location of custom peak file. "
        "The peak file is BED formatted with tab seperated. "
        "The first column is chromsome, the second is chromStart, and the third is chromEnd.")
    group_peak.add_argument("--shortpeak", dest = "shortpeak", action = "store_true", 
        help = "Whether or not to call peaks from short fragments (shorter than 150bp). If set, "
        "MAESTRO will merge the peaks called from all fragments and those called from short fragments, "
        "and then use the merged peak file for further analysis."
        "If not (by default), the pipeline will only use peaks called from all fragments.")
    
    # Gene score arguments
    group_genescore = workflow.add_argument_group("Gene score arguments")
    group_genescore.add_argument("--genedistance", dest = "genedistance", default = 10000, type = int, 
        help = "Gene score decay distance, could be optional from 1kb (promoter-based regulation) "
        "to 10kb (enhancer-based regulation). DEFAULT: 10000.")

    # Signature file arguments
    group_signature = workflow.add_argument_group("Cell signature arguments")
    group_signature.add_argument("--signature", dest = "signature", action = "store_true", 
        help = "Whether or not to provide custom cell signatures. If set, users need to "
        "provide the file location of cell signatures through '--signature-file'. By default (not set), "
        "the pipeline will use the built-in immune cell signature adapted from CIBERSORT.")
    group_signature.add_argument("--signature-file", dest = "signature_file", type = str, default = "", 
        help = "If '--signature' is set, please provide the file location of custom cell signatures. "
        "The signature file is tab-seperated. The first column is cell type, and the second column is signature gene.")
        
    return


def scrna_parser(subparsers):
    """
    Add main function init-scatac argument parsers.
    """

    workflow = subparsers.add_parser("scrna-init", help = "Initialize the MAESTRO scRNA-seq workflow in a given directory. "
        "This will install a Snakefile and a config file in this directory. "
        "You can configure the config file according to your needs, and run the workflow with Snakemake.")

    # Input files arguments
    group_input = workflow.add_argument_group("Input files arguments")
    group_input.add_argument("--platform", dest = "platform", default = "10x-genomics", 
        choices = ["10x-genomics", "Dropseq", "Smartseq2"], 
        help = "Platform of single cell RNA-seq. DEFAULT: 10x-genomics.")
    group_input.add_argument("--fastq-dir", dest = "fastq_dir", type = str, default = "",  
        help = "Directory where fastq files are stored")
    group_input.add_argument("--fastq-prefix", dest = "fastq_prefix", type = str, default = "", 
        help = "Sample name of fastq file, only for the platform of '10x-genomics'. "
        "If there is a file named pbmc_1k_v2_S1_L001_I1_001.fastq.gz, the prefix is 'pbmc_1k_v2'.")
    group_input.add_argument("--fastq-barcode", dest = "fastq_barcode", type = str, default = "", 
        help = "Specify the barcode fastq file, only for the platform of 'Dropseq'. "
        "If there are multiple pairs of fastq, please provide a comma-separated list of barcode fastq files."
        "For example, --fastq-barcode test1_1.fastq,test2_1.fastq")
    group_input.add_argument("--fastq-transcript", dest = "fastq_transcript", type = str, default = "", 
        help = "Specify the transcript fastq file, only for the platform of 'Dropseq'. "
        "If there are multiple pairs of fastq, please provide a comma-separated list of barcode fastq files."
        "For example, --fastq-barcode test1_2.fastq,test2_2.fastq")
    group_input.add_argument("--species", dest = "species", default = "GRCh38",
        choices = ["GRCh38", "GRCm38"], type = str, 
        help = "Species (GRCh38 for human and GRCm38 for mouse). DEFAULT: GRCh38.")

    # Output arguments
    group_output = workflow.add_argument_group("Running and output arguments")
    group_output.add_argument("--cores", dest = "cores", default = 8, 
        type = int, help = "The number of cores to use. DEFAULT: 8.")
    group_output.add_argument("--rseqc", dest = "rseqc", action = "store_true", 
        help = "Whether or not to run RSeQC. "
        "If set, the pipeline will include the RSeQC part and then takes a longer time. "
        "By default (not set), the pipeline will skip the RSeQC part.")
    group_output.add_argument("-d", "--directory", dest = "directory", type = str, default = "MAESTRO", 
        help = "Path to the directory where the workflow shall be initialized and results shall be stored. DEFAULT: MAESTRO.")
    group_output.add_argument("--outprefix", dest = "outprefix", type = str, default = "MAESTRO", 
        help = "Prefix of output files. DEFAULT: MAESTRO.")

    # Quality control cutoff
    group_cutoff = workflow.add_argument_group("Quality control arguments")
    group_cutoff.add_argument("--count-cutoff", dest = "count_cutoff", default = 1000, type = int,
        help = "Cutoff for the number of count in each cell. DEFAULT: 1000.")
    group_cutoff.add_argument("--gene-cutoff", dest = "gene_cutoff", default = 500, type = int,
        help = "Cutoff for the number of genes included in each cell. DEFAULT: 500.")   

    # Reference genome arguments
    group_reference = workflow.add_argument_group("Reference genome arguments")
    group_reference.add_argument("--mapindex", dest = "mapindex", 
        default = "/home1/wangchenfei/annotations/hg38/STAR_2.7.3a", 
        help = "Genome index directory for STAR. Users can just download the index file "
        "from http://cistrome.org/~chenfei/MAESTRO/giggle.tar.gz and decompress it.")
    # group_reference.add_argument("--mapindex", dest = "mapindex", 
    #     default = "/home1/wangchenfei/annotations/refdata-cellranger-GRCh38-3.0.0/star", 
    #     help = "Genome index directory for STAR. If the platform is not '10x-genomics', please specify it. "
    #     "Users can just use the index file in the reference required for Cell Ranger."
    #     "For example, 'refdata-cellranger-GRCh38-3.0.0/star'.")
    # group_reference.add_argument("--cellranger", dest = "cellranger", 
    #     default = "/home1/wangchenfei/annotations/refdata-cellranger-GRCh38-3.0.0", 
    #     help = "Genome annotation file downloaded from 10x-genomics "
    #     "(https://support.10xgenomics.com/single-cell-gene-expression/software/downloads/latest) "
    #     "required for Cell Ranger.")
    group_reference.add_argument("--rsem", dest = "rsem", 
        default = "/home1/wangchenfei/annotations/hg38/RSEM_ref/GRCh38", 
        help = "The prefix of transcript references for RSEM used by rsem-prepare-reference. "
        "Users can directly download the annotation file from "
        "http://cistrome.org/~chenfei/MAESTRO/giggle.tar.gz and decompress it.")

    # Barcode arguments
    group_barcode = workflow.add_argument_group("Barcode arguments, for platform of 'Dropseq' or '10x-genomics'")
    group_barcode.add_argument("--whitelist", dest = "whitelist", type = str, 
        default = "/home1/wangchenfei/Tool/cellranger-3.1.0/cellranger-cs/3.1.0/lib/python/cellranger/barcodes/737K-august-2016.txt",
        help = "If the platform is 'Dropseq' or '10x-genomics', please specify the barcode library (whitelist) "
        "so that the pipeline STARsolo can do the error correction and demultiplexing of cell barcodes. "
        "The 10X Chromium whitelist file can be found inside the CellRanger distribution. "
        "Please make sure that the whitelist is compatible with the specific version of the 10X chemistry: V2 or V3. "
        "For example, in CellRanger 3.1.0, the V2 whitelist is "
        "'cellranger-3.1.0/cellranger-cs/3.1.0/lib/python/cellranger/barcodes/737K-august-2016.txt'. "
        "The V3 whitelist is 'cellranger-3.1.0/cellranger-cs/3.1.0/lib/python/cellranger/barcodes/3M-february-2018.txt'. ")
    group_barcode.add_argument("--barcode-start", dest = "barcode_start", type = int, default = 1,
        help = "The start site of each barcode. DEFAULT: 1. ")
    group_barcode.add_argument("--barcode-length", dest = "barcode_length", type = int, default = 16,
        help = "The length of cell barcode. For 10x-genomics, the length of barcode is 16. DEFAULT: 16. ")
    group_barcode.add_argument("--umi-start", dest = "umi_start", type = int, default = 17,
        help = "The start site of UMI. DEFAULT: 17. ")
    group_barcode.add_argument("--umi-length", dest = "umi_length", type = int, default = 10,
        help = "The length of UMI. For 10x-genomics, the length of V2 chemistry is 10. "
        "For 10X V3 chemistry, the length is 12. DEFAULT: 10. ")

    # Regulator identification
    group_regulator = workflow.add_argument_group("Regulator identification arguments")
    group_regulator.add_argument("--method", dest = "method", type = str, 
        choices = ["RABIT", "LISA"], default = "LISA",
        help = "Method to predict driver regulators.")
    group_regulator.add_argument("--rabitlib", dest = "rabitlib", type = str, 
        default = "/home1/wangchenfei/Project/SingleCell/scATAC/Code/MAESTRO/MAESTRO/annotations/Rabit_lib",
        help = "Path of the rabit annotation file required for regulator identification. "
        "Please download the annotation file from "
        "http://cistrome.org/~chenfei/MAESTRO/rabit.tar.gz and decompress it.")
    group_regulator.add_argument("--lisamode", dest = "lisamode", type = str, default = "local", choices = ["local", "web"],
        help = "Mode to Run LISA, 'local' or 'web'. If the mode is set as 'local', "
        "please install LISA (https://github.com/qinqian/lisa) and download pre-computed datasets following the instructions. "
        "The 'web' mode is to run online version of LISA. In consideration of the connection issue and size of datasets, "
        "the 'local' mode is recommended to run the whole MAESTRO pipeline.")
    group_regulator.add_argument("--lisaenv", dest = "lisaenv", type = str, default = "lisa",
        help = "Name of lisa environment (only if method is set to lisa and lisamode is set to local). DEFAULT: lisa.")
    group_regulator.add_argument("--condadir", dest = "condadir", type = str, 
        default = "/home1/wangchenfei/miniconda3",
        help = "Directory where miniconda or anaconda is installed "
        "(only if method is set to lisa and lisamode is set to local). For example, '/home1/wangchenfei/miniconda3'.")

    # Signature file arguments
    group_signature = workflow.add_argument_group("Cell signature arguments")
    group_signature.add_argument("--signature", dest = "signature", action = "store_true", 
        help = "Whether or not to provide custom cell signatures. If set, users need to "
        "provide the file location of cell signatures through '--signature-file'. By default (not set), "
        "the pipeline will use the built-in immune cell signature adapted from CIBERSORT.")
    group_signature.add_argument("--signature-file", dest = "signature_file", type = str, default = "",
        help = "If '--signature' is set, please provide the file location of custom cell signatures. "
        "The signature file is tab-seperated without header. The first column is cell type, and the second column is signature gene.")
    
    return


def integrate_parser(subparsers):
    """
    Add main function init-scatac argument parsers.
    """

    workflow = subparsers.add_parser("integrate-init", help = "Initialize the MAESTRO integration workflow in a given directory. "
        "This will install a Snakefile and a config file in this directory. "
        "You can configure the config file according to your needs, and run the workflow with Snakemake.")

    # Input files arguments
    group_input = workflow.add_argument_group("Input files arguments")
    group_input.add_argument("--rna-object", dest = "rna_object", default = "", type = str,
        help = "Path of scRNA Seurat object generated by MAESTRO scRNA pipeline.")
    group_input.add_argument("--atac-object", dest = "atac_object", default = "", type = str,
        help = "Path of scATAC Seurat object generated by MAESTRO scATAC pipeline.")

    # Output arguments
    group_output = workflow.add_argument_group("Running and output arguments")
    group_output.add_argument("-d", "--directory", dest = "directory", default = "MAESTRO", 
        help = "Path to the directory where the workflow shall be initialized and results shall be stored. DEFAULT: MAESTRO.")
    group_output.add_argument("--outprefix", dest = "outprefix", type = str, default = "MAESTRO", 
        help = "Prefix of output files. DEFAULT: MAESTRO.")

    return


def scatac_config(args):
    """
    Generate scatac config.yaml file.
    """

    try:
        os.makedirs(args.directory)
    except OSError:
        # either directory exists (then we can ignore) or it will fail in the
        # next step.
        pass


    pkgpath = resource_filename('MAESTRO', 'Snakemake')
    template_file = os.path.join(pkgpath, "scATAC", "config_template.yaml")
    # template_file = "/Users/dongqing/Documents/Project/SingleCell/scATAC/Code/Snakemake/scATAC/config_template.yaml"
    configfile = os.path.join(args.directory, "config.yaml")
    config_template = Template(open(template_file, "r").read(), trim_blocks=True, lstrip_blocks=True)
    with open(configfile, "w") as configout:
        configout.write(config_template.render(
            fastqdir = args.fastq_dir, 
            fastqprefix = args.fastq_prefix,
            species = args.species,
            platform = args.platform,
            outprefix = args.outprefix,
            whitelist = args.whitelist,
            cores = args.cores,
            count = args.count_cutoff,
            frip = args.frip_cutoff,
            signature = args.signature,
            signaturefile = args.signature_file,
            custompeaks = args.custompeak,
            custompeaksloc = args.custompeak_file,
            shortpeaks = args.shortpeak,
            genedistance = args.genedistance,
            giggleannotation = args.giggleannotation,
            fasta = args.fasta))
    
    source = os.path.join(pkgpath, "scATAC", "Snakefile")
    target = os.path.join(args.directory, "Snakefile")
    shutil.copy(source, target)


def scrna_config(args):
    """
    Generate scrna config.yaml file.
    """

    try:
        os.makedirs(args.directory)
    except OSError:
        # either directory exists (then we can ignore) or it will fail in the
        # next step.
        pass

    pkgpath = resource_filename('MAESTRO', 'Snakemake')
    template_file = os.path.join(pkgpath, "scRNA", "config_template.yaml")
    # template_file = "/Users/dongqing/Documents/Project/SingleCell/scATAC/Code/Snakemake/scRNA/config_template.yaml"
    configfile = os.path.join(args.directory, "config.yaml")
    config_template = Template(open(template_file, "r").read(), trim_blocks=True, lstrip_blocks=True)
    with open(configfile, "w") as configout:
        configout.write(config_template.render(
            fastqdir = args.fastq_dir, 
            fastqprefix = args.fastq_prefix,
            species = args.species,
            platform = args.platform,
            outprefix = args.outprefix,
            rseqc = args.rseqc,
            cores = args.cores,
            count = args.count_cutoff,
            gene = args.gene_cutoff,
            signature = args.signature,
            signaturefile = args.signature_file,
            method = args.method,
            rabitlib = args.rabitlib,
            lisamode = args.lisamode,
            lisaenv = args.lisaenv,
            condadir = args.condadir,
            mapindex = args.mapindex,
            rsem = args.rsem,
            whitelist = args.whitelist,
            barcodestart = args.barcode_start,
            barcodelength = args.barcode_length,
            umistart = args.umi_start,
            umilength = args.umi_length,
            barcode = args.fastq_barcode,
            transcript = args.fastq_transcript))

    source = os.path.join(pkgpath, "scRNA", "Snakefile")
    target = os.path.join(args.directory, "Snakefile")
    shutil.copy(source, target)


def integrate_config(args):
    """
    Generate integrate config.yaml file.
    """

    try:
        os.makedirs(args.directory)
    except OSError:
        # either directory exists (then we can ignore) or it will fail in the
        # next step.
        pass

    pkgpath = resource_filename('MAESTRO', 'Snakemake')
    template_file = os.path.join(pkgpath, "integrate", "config_template.yaml")
    # template_file = "/Users/dongqing/Documents/Project/SingleCell/scATAC/Code/Snakemake/integrate/config_template.yaml"
    configfile = os.path.join(args.directory, "config.yaml")
    config_template = Template(open(template_file, "r").read(), trim_blocks=True, lstrip_blocks=True)
    with open(configfile, "w") as configout:
        configout.write(config_template.render(
            rnaobject = args.rna_object, 
            atacobject = args.atac_object,
            outprefix = args.outprefix))

    source = os.path.join(pkgpath, "integrate", "Snakefile")
    target = os.path.join(args.directory, "Snakefile")
    shutil.copy(source, target)

