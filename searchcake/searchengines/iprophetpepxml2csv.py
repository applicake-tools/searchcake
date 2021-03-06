#!/usr/bin/env python
# -*- coding: utf-8  -*-

from __future__ import print_function

import sys
from pyteomics import pepxml

import csv
import os

from applicake2.base.app import BasicApp
from applicake2.base.coreutils.arguments import Argument
from applicake2.base.coreutils.keys import Keys, KeyHelp
from searchcake.prophets.ParsePepXMLProbablities import parsePepXMLProbToErroMapping

class IprohetPepXML2CSV(BasicApp):
    def add_args(self):
        return [
            Argument(Keys.WORKDIR, KeyHelp.WORKDIR),
            Argument(Keys.PEPXML, Keys.PEPXML),
        ]


    def run(self, log, info):
        """
        After ProteinQuantifier puts abundances from consensusXML to csv,
        put abundances back to original protXML file.
        """
        # correct csv with right header
        pepxml_in = info[Keys.PEPXML]
        info['PEPCSV'] = os.path.join(info[Keys.WORKDIR], "ipeptide.tsvh")
        info['PEPCSVERROR'] = os.path.join(info[Keys.WORKDIR], "error.tsvh")

        csv_out = info['PEPCSV']
        self.iprophetpepxml_csv(pepxml_in, csv_out)
        parsePepXMLProbToErroMapping(pepxml_in, info['PEPCSVERROR'] )
        return info

    @staticmethod
    def iprophetpepxml_csv(infile, outfile):
        """
        :param infile: input pepxml
        :param outfile: outcsv
        :return:
        """
        # outfile = os.path.splitext(infile)[0] + '.csv'
        reader = pepxml.read(infile)
        f = open(outfile, 'wb')
        writer = csv.writer(f, delimiter='\t')
        # modifications_example = [{'position': 20, 'mass': 160.0306}]

        header_set = False

        nr_rows = 0
        result = {}
        for hit in reader:
            if 'error_point' in hit:
                print (hit)

#wenguang: remove all decoy hits!
            if 'search_hit' in hit and hit['search_hit'][0]['proteins'][0]['protein'].find("DECOY") == -1:
                #continue
                #else :
                # result = hit#
                #print(hit['search_hit'][0]['proteins'][0]['protein'])
                nr_rows +=1
                result['retention_time_sec'] = hit['retention_time_sec']
                result['assumed_charge'] = hit['assumed_charge']
                result['spectrum'] = hit['spectrum']
                result['nrhit'] = len(hit['search_hit'])
                search_hit = hit['search_hit'][0]

                result['modified_peptide'] = search_hit['modified_peptide']
                result['search_hit'] = search_hit['peptide']
                analysis_result = search_hit['analysis_result'][1]
                iprophet_probability = analysis_result['interprophet_result']['probability']
                result['iprophet_probability'] = iprophet_probability
                result['protein_id'] = search_hit['proteins'][0]['protein']
                result['nrproteins'] = len(search_hit['proteins'])
                if not header_set:
                    writer.writerow(result.keys())
                    header_set = True
                writer.writerow(result.values())
        print(nr_rows)
        f.close()


if __name__ == "__main__":
    infile = "/mnt/Systemhc/wshao/test_2/search/Kowalewskid_160207_Rammensee_Germany_PBMC_Buffy18/InterProphet/iprophet.pep.xml"#sys.argv[1]
    outfile = "dummm.csv"#sys.argv[2]
    sys.argv = ['--INPUT', '/mnt/Systemhc/wshao/test_2/search/datasetiprophet.ini', '--OUTPUT', 'test.ini']
    IprohetPepXML2CSV.main()
    #IprohetPepXML2CSV.iprophetpepxml_csv(infile, outfile)



