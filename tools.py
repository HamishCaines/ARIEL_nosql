def load_json(infile):
    """
    Loads database from json output file, created by make_database.py
    :param infile: location of the json file
    :return: list of Target objects containing all the required information
    """
    import json
    import target
    with open(infile) as f:
        data = json.load(f)  # loads a set json outputs into a list
    targets = []
    for single in data:  # create Target object for each json, and load json into it
        new_target = target.Target().init_from_json(single)
        targets.append(new_target)  # add to list
    return targets


def load_telescopes(filename):
    """
    Loads telescope parameters from a .csv file ans stores as a list of Telescope objects
    :param filename: location of data file to be loaded
    :return: List of Telescope objects
    """
    import numpy as np
    import telescope
    data = np.genfromtxt(filename, dtype=str, skip_header=1, delimiter=',')  # read csv data
    telescopes = []
    for single in data:  # create Telescope object for each row and load data into it
        telescopes.append(telescope.Telescope().gen_from_csv(single))
    return telescopes


class UndefinedEndDateError(Exception):
    pass


class UndefinedStartDateError(Exception):
    pass


class StartingInPastError(Exception):
    pass


class OverspecifiedInputsError(Exception):
    pass


class InvalidArgumentError(Exception):
    pass


def check_input_dates(args):
    from datetime import datetime, timedelta
    if args.mode == 'simulate':
        start = datetime(year=2019, month=6, day=12)
        end = datetime(year=2030, month=6, day=12)

    else:
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

    return start, end


def increment_total_night(start, interval, telescopes):
    """
    Keep a running total of the total available observing hours through out simulation by calculating sunset and
    rise for each day in specified window
    :param telescopes:
    :param start: Start of window: datetime
    :param interval: Length of window: datetime
    """
    from datetime import timedelta
    import mini_staralt

    end = start + interval
    day = timedelta(days=1)
    total_night_interval = timedelta(days=0)
    clear_night_interval = timedelta(days=0)
    while start < end:
        for telescope in telescopes:  # calculate sunset/rise at each site
            sunset, sunrise = mini_staralt.sun_set_rise(start, lon=telescope.lon, lat=telescope.lat,
                                                        sundown=-12)
            duration = (sunrise - sunset)*telescope.copies
            total_night_interval += duration  # add duration to counter
            month = start.strftime('%B')
            clear_night_interval += duration * telescope.weather[month]
            #print(f'Clear: {clear_night_interval}')
        start += day  # increment day

    return total_night_interval, clear_night_interval
