#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from egvqa_pilot.runner import ExperimentRunner

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--dataset',default='data/downloads/egvqa-pilot');parser.add_argument('--stage',choices=['e1','e2','core'],default='core')
    args=parser.parse_args();runner=ExperimentRunner(args.run,args.dataset)
    try:
        if args.stage in ['e1','core']:runner.run_e1()
        if args.stage in ['e2','core']:runner.run_e2()
    finally:runner.close()
if __name__=='__main__':main()
