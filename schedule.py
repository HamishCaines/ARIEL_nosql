#################################################################
# Schedules the upcoming observable transits for targets that
# require observation.
# Takes a target list and dataset produced by ETD_query.py to
# make the calculation.
# Transits are calculated for each telescope provided, and each
# gets a list of observable transits.
# Hamish Caines 10/2019
# TODO: add simulator component
#################################################################


class UndefinedEndDateError(Exception):
    pass


class UndefinedStartDateError(Exception):
    pass


class StartingInPastError(Exception):
    pass


class OverspecifiedInputsError(Exception):
    pass


def schedule(args):
    from datetime import datetime, timedelta
    from os import listdir, remove
    import tools

    infile = '../starting_data/database.json'
    targets = tools.load_json(infile)
    telescope_file = args.te
    threshold = args.th
    # check for over specification
    if args.st is not None and args.ed is not None and args.wl is not None:
        raise OverspecifiedInputsError
    # work from today through window
    if args.st is None and args.ed is None:
        if args.wl is None:
            raise UndefinedStartDateError
        else:
            start = datetime.today()
            end = start + timedelta(days=args.wl)
    # work from specified date through window
    elif args.st is not None and args.ed is None:
        if args.wl is None:
            raise UndefinedEndDateError
        else:
            start = datetime.strptime(args.st, '%Y-%m-%d')
            end = start + timedelta(days=args.wl)
            if end < datetime.today():
                raise StartingInPastError
    # work from today to end date
    elif args.st is None and args.ed is not None:
        end = datetime.strptime(args.ed, '%Y-%m-%d')
        if end < datetime.today():
            raise StartingInPastError
        else:
            start = datetime.today()
    # work between two dates
    else:
        start = datetime.strptime(args.st, '%Y-%m-%d')
        end = datetime.strptime(args.ed, '%Y-%m-%d')

    depth_limit = 0.01
    telescopes = tools.load_telescopes('../telescopes/'+telescope_file)

    print('Using', len(telescopes), 'telescopes')
    print('Forecasting from', start.date(), 'until', end.date())

    telescope_files = listdir('../scheduling_data/')  # check if output files already exist
    for telescope in telescopes:
        if telescope.name+'.csv' in telescope_files:  # remove output files that exist for telescopes
            remove('../scheduling_data/'+telescope.name+'.csv')
        with open(telescope.name+'.csv', 'a+') as f:  # add header row to new files
            f.write('#Name, Ingress(UTC), Center(UTC), Egress(UTC), PartialTransit')

    if 'all_telescopes.csv' in telescope_files:
        remove('../scheduling_data/all_telescopes.csv')  # remove total output file if exists
    with open('../scheduling_data/all_telescopes.csv', 'a+') as f:
        f.write('#Name, Site, Ingress(UTC), Center(UTC), Egress(UTC), PartialTransit')  # add header row to new file

    # determine which targets require observations
    required_targets = []
    for target in targets:
        if target.depth is not None:  # check for valid depth
            if target.real and float(target.depth) > depth_limit:  # check for real target with required depth
                if target.calculate_expiry(threshold, start):  # run expiry calculation
                    required_targets.append(target)  # add to list if required

    required_targets.sort(key=lambda x: x.current_err, reverse=True)  # prioritise by largest current timing error

    all_transits = []
    for target in required_targets:  # loop through needed targets
        # obtain all visible transits for required targets, with observing site
        visible_transits = target.transit_forecast(start, end, telescopes)
        for visible in visible_transits:  # add to list
            all_transits.append(visible)
    all_transits.sort(key=lambda x: x.center)  # sort by date

    # output required transits
    for single in all_transits:
        # output all to one document, with site data
        with open('../scheduling_data/all_telescopes.csv', 'a+') as f:
            f.write('\n' + single.name + ', ' + single.telescope + ', ' + single.ingress.strftime(
                "%Y-%m-%dT%H:%M:%S") + ', ' + single.center.strftime(
                "%Y-%m-%dT%H:%M:%S") + ', ' + single.egress.strftime("%Y-%m-%dT%H:%M:%S")+', '+str(single.partial))
            f.close()
        # output to individual documents per telescope
        with open('../scheduling_data/'+single.telescope+'.csv', 'a+') as f:
            f.write('\n' + single.name + ', ' + single.ingress.strftime(
                "%Y-%m-%dT%H:%M:%S") + ', ' + single.center.strftime(
                "%Y-%m-%dT%H:%M:%S") + ', ' + single.egress.strftime("%Y-%m-%dT%H:%M:%S")+', '+str(single.partial))
            f.close()

    print('Forecast', len(all_transits), 'visible transits')
