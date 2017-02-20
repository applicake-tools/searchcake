#!/usr/bin/env python
import os
import re

from searchcake.utils.fdr import get_iprob_for_fdr
from applicake2.base.app import WrappedApp
from applicake2.base.apputils import validation
from applicake2.base.coreutils.arguments import Argument
from applicake2.base.coreutils.keys import Keys, KeyHelp


class SpectrastRTcalib(WrappedApp):
    """
    Create raw text library with iRT correction and without DECOYS_ from pepxml
    """
    def add_args(self):
        return [
            Argument(Keys.WORKDIR, KeyHelp.WORKDIR),
            Argument(Keys.MZXML, KeyHelp.MZXML),

            Argument(Keys.PEPXML, KeyHelp.PEPXML),
            Argument('TPPDIR','tpp directory', default=''),
            Argument('MAYUOUT', 'mayu out csv'),
            Argument('FDR_TYPE', "type of FDR: iprophet/mayu m/pep/protFDR",default='iprophet'),
            Argument("FDR_CUTOFF", "cutoff for FDR",default=0.1),

            Argument('RUNRT', "Boolean to activate iRT calibration",default=False),
            Argument('RSQ_THRESHOLD', 'specify r-squared threshold to accept linear regression' , default =0.9 ),
            Argument('RTKIT', 'RT kit (file)'),
            Argument('MS_TYPE', 'ms instrument type'),
            Argument('CONSENSUS_TYPE', 'consensus type consensus/best replicate',default='consensus')
        ]

    def prepare_run(self, log, info):
        # symlink the pepxml and mzxml files first into a single directory
        peplink = os.path.join(info[Keys.WORKDIR], os.path.basename(info[Keys.PEPXML]))
        #log.debug('create symlink [%s] -> [%s]' % (info[Keys.PEPXML], peplink))
        #os.symlink(info[Keys.PEPXML], peplink)


        info['SPLOG'] = os.path.join(info[Keys.WORKDIR], 'spectrast.log')

        # get iProb corresponding FDR for IDFilter
        info['IPROB'], info['FDR'] = get_iprob_for_fdr(info['FDR_CUTOFF'], info['FDR_TYPE'],
                                                       mayuout=info.get('MAYUOUT'),
                                                       pepxml=info.get(Keys.PEPXML))

        if info.get("RUNRT") == "True":
            rtcorrect = "-c_IRT%s -c_IRR" % info['RTKIT']
        else:
            rtcorrect = ""

        rtcalib_base = os.path.join(info[Keys.WORKDIR], 'RTcalib')
        rtcalib = rtcalib_base + '.splib'

        consensustype = ""
        if info['CONSENSUS_TYPE'] == "Consensus":
            consensustype = "C"
        elif info['CONSENSUS_TYPE'] == "Best replicate":
            consensustype = "B"

        consensus_base = os.path.join(info[Keys.WORKDIR], 'consensus')
        consensus = consensus_base + '.splib'
        info['SPLIB'] = consensus

        command1 = "spectrast -L{slog} -c_RDYDECOY -cI{mstype} -cP{iprob} {rtcorrect} -cN{rtcalib_base} {peplink}".format(
            slog=info['SPLOG'],mstype=info['MS_TYPE'],iprob = info['IPROB'],rtcorrect=rtcorrect,
            rtcalib_base= rtcalib_base, peplink = peplink)

        command2 = "spectrast -L{slog} -c_BIN! -cA{consensustype} -cN{consensus_base} {rtcalib}".format(
            slog=info['SPLOG'],consensustype=consensustype, consensus_base=consensus_base,rtcalib=rtcalib)
                      #info['SPLOG'], info['MS_TYPE'], info['IPROB'], rtcorrect, rtcalib_base, peplink,
                      #info['SPLOG'], consensustype, consensus_base, rtcalib)

        return info, [command1, command2]

    def validate_run(self, log, info, exit_code, stdout):
        if info['RUNRT'] == 'True':
            # Spectrast imports sample *whitout error* when no iRTs are found. Thus look for "Comment:" entries without
            # iRT= attribute in splib
            notenough = set()
            for line in open(info['SPLIB']).readlines():
                if "Comment:" in line and not "iRT=" in line:
                    samplename = re.search("RawSpectrum=([^\.]*)\.", line).group(1)
                    notenough.add(samplename)
            if notenough:
                log.error("No/not enough iRT peptides found in sample(s): " + ", ".join(notenough))

            #when irt.txt not readable: PEPXML IMPORT: Cannot read landmark table. No RT normalization will be performed.
            rtcalibfailed = False
            for line in open(info['SPLOG']).readlines():
                if "Cannot read landmark table" in line:
                    log.error("Problem with reading rtkit file %s!"%info['RTKIT'])
                    rtcalibfailed = True

            # Parse logfile to see whether R^2 is high enough. Example log for failed calibration (line 3 only when <0.9):
            # PEPXML IMPORT: RT normalization by linear regression. Found 10 landmarks in MS run "CHLUD_L110830_21".
            # PEPXML_IMPORT: Final fitted equation: iRT = (rRT - 1758) / (8.627); R^2 = 0.5698; 5 outliers removed.
            # ERROR PEPXML_IMPORT: R^2 still too low at required coverage. No RT normalization performed. Consider...
            rsqlow = False
            for line in open(info['SPLOG']).readlines():
                if "Final fitted equation:" in line:
                    samplename = prevline.strip().split(" ")[-1]
                    rsq = line.split()[-4].replace(";", "")
                    if float(rsq) < float(info['RSQ_THRESHOLD']):
                        log.error(
                            "R^2 of %s is below threshold of %s for %s" % (rsq, info['RSQ_THRESHOLD'], samplename))
                        rsqlow = True
                    else:
                        log.debug("R^2 of %s is OK for %s" % (rsq, samplename))
                else:
                    prevline = line

            # Raise only here to have all errors shown
            if rsqlow or rtcalibfailed or notenough:
                raise RuntimeError("Error in iRT calibration.")

        # Double check "Spectrast finished ..."
        if not " without error." in stdout:
            raise RuntimeError("SpectraST finished with some error!")

        validation.check_exitcode(log, exit_code)
        validation.check_file(log, info['SPLIB'])
        return info


if __name__ == "__main__":
    SpectrastRTcalib.main()
