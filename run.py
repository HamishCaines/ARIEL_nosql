import argparse
from os import getcwd, chdir, mkdir
import threading
import multiprocessing

import settings


def parse_arguments():
    parser = argparse.ArgumentParser(description='Run workhouse code in either Scheduler or Simulator mode.'
                                                 'All keywords used for both modes unless specified.')
    parser.add_argument('-mode', choices=['schedule', 'simulate'], help='Operation mode')
    parser.add_argument('-te', help='.csv file containing the telescope network to be used')
    parser.add_argument('-th', type=float, help='Accuracy threshold to be aimed for')
    parser.add_argument('-wl', type=int, required=False, help='Length of window to be scheduled over: Only used by Schedule')
    parser.add_argument('-st', required=False, help='Start date for scheduling or simulation')
    parser.add_argument('-ed', required=False, help='End date for scheduling or simulation')
    parser.add_argument('-rp', type=int, required=False, help='Number of repeats for simulation')
    args = parser.parse_args()

    return args




def run(process):
    setting_data = settings.Settings('settings.dat')
    thresholds = setting_data.threshold_value
    networks = setting_data.telescopes
    #args = parse_arguments()
    #print(vars(args))
    if setting_data.mode == 'SIMULATE':
        starting_dir = f'{getcwd()}/simulation_data/{setting_data.directory}_{process}'
    elif setting_data.mode == 'SCHEDULE':
        starting_dir = f'{getcwd()}/scheduling_data/{setting_data.directory}'
    else:
        raise Exception

    mkdir(starting_dir)

    setting_data.repeats = 1
    count = 1
    while count < 5:
        for network in networks:
            single_run_settings = setting_data
            single_run_settings.telescopes = network
            for value in thresholds:
                single_run_settings.threshold_value = value
                if setting_data.mode == 'SCHEDULE':  # schedule mode
                    import schedule
                    schedule.schedule(single_run_settings)
                if setting_data.mode == 'SIMULATE':  # simulate mode
                    import simulate
                    simulate.simulate(single_run_settings, starting_dir, count)

        count += 1
    # TODO: Need to add the changes discussed with Marco et al, think about how to model amateurs
    # TODO: Think about how many targets are visible from the ground

def main():
    for i in range(0, 2):
        print(f'Starting process {i}')
        p = multiprocessing.Process(target=run, args=(i,))
        p.start()

if __name__ == '__main__':
    main()
