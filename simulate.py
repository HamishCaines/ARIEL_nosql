def simulate(args):
    from os import listdir, mkdir, chdir
    from shutil import rmtree
    import tools

    # TODO: add depth handling here

    # check if number of repeats is specified
    if args.rp is None:  # if not specified, set to 1
        runs = 1
    else:
        runs = args.rp

    count = 1  # run count
    # obtain telescope and threshold to use
    telescope_file = args.te
    threshold = args.th
    simulation_name = telescope_file.split('.')[0] + '_' + str(threshold)  # create simulation number
    # check existing simulations for this one
    simulation_files = listdir('../simulation_data/')
    telescopes = tools.load_telescopes('../telescopes/' + telescope_file)

    if simulation_name in simulation_files:
        print('Simulation', simulation_name, 'already exists. Replace?')  # ask if user wants to delete existing simulations
        replace = input('Simulation ' + simulation_name + ' already exists. Replace? (y/n) ')
        if replace == 'y':
            replace = True
        else:
            replace = False
        if replace:  # if yes, delete
            rmtree('../simulation_data/' + simulation_name)
        else:  # if no, stop script
            raise Exception

    # make new directory for simulation and cd into it
    mkdir('../simulation_data/' + simulation_name)
    chdir('../simulation_data/' + simulation_name)

    # initialise results file
    with open('results.csv', 'a+') as f:
        f.write('#Run, Performance(%), TotalObservations, TotalObsDays, TotalNightDays, PercentNightUsed')
        f.close()

    # loop for number of runs specified
    while count <= runs:
        run_name = 'run'+str(count)  # increment run number
        run_sim(args, run_name, telescopes)  # new simulation run
        count += 1


def run_sim(args, run_name, telescopes):
    import tools
    from os import mkdir, chdir
    from datetime import timedelta
    import numpy as np

    start, end = tools.check_input_dates(args)  # obtain start and end dates
    threshold = args.th  # obtain threshold

    # load targets from database into objects
    infile = '../../starting_data/database.json'
    targets = tools.load_json(infile)

    depth_data = np.genfromtxt('../../starting_data/depth_limits_10.csv',
                               delimiter=',')  # load coefficients for depth calculations
    for target in targets:
        target.calculate_expiry(threshold)  # calculate expiry date for target
        target.determine_telescope_visibility(telescopes, depth_data)

    targets.sort(key=lambda x: x.current_err)  # sort by current timing error

    interval = timedelta(days=7)  # length of individual time blocks

    # made directory for current run and cd into it
    mkdir(run_name)
    chdir(run_name)
    # initialise files for scheduled observations
    for telescope in telescopes:
        with open(telescope.name+'.csv', 'a+') as f:  # add header row to new files
            f.write('#Name, Start(UTC), End(UTC)')
            f.close()

    with open('all_telescopes.csv', 'a+') as f:
        f.write('#Name, Site, Start(UTC), End(UTC)')  # add header row to new file
        f.close()
    print('Using', len(telescopes), 'telescopes')
    print('Simulating from', start.date(), 'until', end.date())

    # initialise counters
    current = start
    tot_obs = 0
    tot_obs_time = timedelta(days=0)
    tot_night_time = timedelta(days=0)
    count, total = 0, 0
    while current < end:
        total = 0
        count = 0
        # obtain the currently required targets
        required_targets = []
        for target in targets:
            if target.depth is not None:  # check for valid depth
                if len(target.observable_from) > 0:  # check for real target with observable
                    total += 1
                    if target.check_if_required(current):  # run check if target is required
                        count += 1
                        required_targets.append(target)  # add to list if required

        required_targets.sort(key=lambda x: x.expiry)  # sort by expiry date
        print(current, len(required_targets), count/total*100, count, total, tot_obs)
        # obtain visible transits for the required targets
        visible_transits = []
        for target in required_targets:
            visible = target.transit_forecast(current, current + interval, telescopes)  # obtain visible transits
            for single in visible:
                visible_transits.append(single)

        # extract the transits visible at each telescope
        for telescope in telescopes:
            telescope.observations = []  # reset observations at each telescope for this window
            matching_transits = []
            for transit in visible_transits:
                if transit.telescope == telescope.name:
                    matching_transits.append(transit)
            # sort transits by number of usable telescopes for each, giving priority to those visible from fewer sites
            matching_transits.sort(key=lambda x: x.visible_from)
            obs_results = telescope.schedule_observations(
                matching_transits)  # schedule matching transits and count time used
            # increment counters
            tot_obs += obs_results[0]
            tot_obs_time += obs_results[1]
            new_data = telescope.simulate_observations()  # simulate the scheduled observations
            # add new data
            for single in new_data:
                for target in targets:
                    if target.name == single[0]:
                        target.observations.append([single[1], single[2], single[3]])  # add new data point to target
                        # reset values to latest observation
                        target.last_epoch = single[1]
                        target.last_tmid = single[2]
                        target.last_tmid_err = single[3]
                        target.period_fit()  # run period fit to refine the period error
                        target.calculate_expiry(threshold)  # recalculate the expiry date based on the new data

        tot_night_time += tools.increment_total_night(current, interval, telescopes)
        current += interval  # increment time block
    chdir('../')  # change out of run module
    percent = 100-(count/total*100)
    # write results for this run to results file
    tot_obs_days = tot_obs_time.total_seconds()/86400
    tot_night_days = tot_night_time.total_seconds()/86400
    with open('results.csv', 'a+') as f:
        f.write('\n' + str(run_name.split('run')[1]) + ', ' + str(percent) + ', ' + str(tot_obs) + ', ' + str(
            tot_obs_days) + ', ' + str(tot_night_days) + ', ' + str(tot_obs_days / tot_night_days * 100))
    print(100-(count/total*100))
