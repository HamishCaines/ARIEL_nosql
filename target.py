class Target:
    """
    Target object, contains information on the target, and can find missing information and calculate expiry date of
    dataset available
    """
    def __init__(self):
        """
        Null constructor
        """
        self.name = None
        self.star = None
        self.planet = None
        self.ra = None
        self.dec = None
        self.period = None
        self.period_err = None
        self.duration = None
        self.last_tmid = None
        self.last_tmid_err = None
        self.last_epoch = None
        self.expiry = None
        self.depth = None
        self.real = None
        self.observations = None
        self.current_err = 0

    def init_from_json(self, json):
        """
        Fills Target object with information from json dictionary
        :param json:
        :return: Filled target object
        """
        self.name = json['name']
        self.star = json['star']
        self.planet = json['planet']
        self.ra = json['ra']
        self.dec = json['dec']
        self.period = json['period']
        self.period_err = json['period_err']
        self.duration = json['duration']
        self.last_tmid = json['last_tmid']
        self.last_tmid_err = json['last_tmid_err']
        self.last_epoch = json['last_epoch']
        self.expiry = json['expiry']
        self.depth = json['depth']
        self.real = json['real']
        self.observations = json['observations']

        return self

    def init_from_list(self, row):
        """
        Fills Target object from row of data from .csv file
        :param row: List of values to be stored
        :return: Filled Target object
        """
        self.name = row[0]
        self.star = row[0][:-1]
        self.planet = row[0][-1]
        self.ra = float(row[1])
        self.dec = float(row[2])
        self.period = float(row[3])
        try:
            self.period_err = float(row[4])
        except ValueError:
            self.period_err = None
        self.duration = float(row[5])
        self.last_tmid = float(row[7])
        try:
            self.last_tmid_err = float(row[8])
        except ValueError:
            self.last_tmid_err = None
        self.last_epoch = float(row[9])
        self.expiry = 0

        if row[6] != '':
            self.depth = row[6]
        else:
            self.depth = None
        if row[10] == '1':
            self.real = True
        else:
            self.real = False
        self.observations = []

        return self

    def __str__(self):
        return self.name+' '+str(self.last_tmid)

    def find_missing_values(self):
        """
        Query exoplanets.org for missing data and store in object
        """
        import requests
        import re

        # build url for specific target, many cases
        url_base = 'http://exoplanets.org/detail/'
        if self.star[0].isdigit():
            number = True
            count = 0
            while number:
                count += 1
                number = self.star[count].isdigit()
            url = url_base + self.star[:count] + '_' + self.star[count:] + '_' + self.planet
        elif self.star[:4] == 'EPIC':
            url = url_base + self.star[:4] + '_' + self.star[4:] + '_' + self.planet
        elif 'GJ' in self.star:
            url = url_base + 'GJ' + '_' + self.star[2:] + '_' + self.planet
        elif 'HD' in self.star:
            url = url_base + 'HD' + '_' + self.star[2:] + '_' + self.planet
        elif 'LHS' in self.star:
            url = url_base + 'LHS' + '_' + self.star[3:] + '_' + self.planet
        elif 'NGTS' in self.star:
            url = url_base + 'NGTS' + '-' + self.star[4:] + '_' + self.planet
        elif 'PH' in self.star:
            url = url_base + 'PH-' + self.star[2:] + '_' + self.planet
        elif 'KPS' in self.star:
            url = url_base + 'KPS' + '-' + self.star[3:] + '_' + self.planet
        elif 'HIP' in self.star:
            url = url_base + 'HIP' + '_' + self.star[3:] + '_' + self.planet
        else:
            url = url_base + self.star + '_' + self.planet

        # obtain html from url
        web_html = str(requests.get(url).content)

        # check for valid planet
        invalid_check = re.findall("(Invalid Planet)", web_html)
        if invalid_check:
            print(url + ' is invalid')
        if not invalid_check:
            # read data
            data = dict(re.findall("\"([\w]+)\":\[([\d\w\.\"\s\/\:\;\%]+)\]", web_html))
            if self.last_tmid_err is None:  # check for missing ephemeris error
                # check for ETD observations
                if len(self.observations) == 0:  # no observations available
                    try:
                        if data['TT'] != 'null' and data['TTUPPER'] != 'null':  # obtain timing data from database
                            # store in object
                            self.last_tmid = float(data['TT']) - 2400000
                            self.last_epoch = 0
                            self.last_tmid_err = data['TTUPPER']

                        else:
                            print('Warning: Target', self.name, 'is missing last_tmid_err')
                    except KeyError:
                        print('Warning: Target', self.name, 'is missing last_tmid_err')

                else:  # observations available
                    last_ob = max(self.observations)
                    self.last_epoch = last_ob[0]
                    self.last_tmid = last_ob[1]
                    self.last_tmid_err = last_ob[2]

            if self.depth is None:  # check for missing transit depth
                try:
                    if data['DEPTH'] != 'null':  # if depth is available, store in object
                        self.depth = float(data['DEPTH'])*1000
                    # if not available, attempt calculation from planet and star radius
                    elif data['RSTAR'] != 'null' and data['R'] != 'null':
                        self.depth = float(data['R'])*0.10049/float(data['RSTAR'])*1000
                    else:
                        print('Warning: Target', self.name, 'is missing depth')
                except KeyError: # if not available, attempt calculation from planet and star radius
                    if data['RSTAR'] != 'null' and data['R'] != 'null':
                        self.depth = float(data['R'])*0.10049/float(data['RSTAR'])
                    else:
                        print('Warning: Target', self.name, 'is missing depth')

    def calculate_expiry(self, threshold):
        """
        Calculate expiry date of a target, the date where the timing error propagates to the set threshold
        :param threshold: Required timing accuracy at ARIEL launch: int
        :return:
        """
        import numpy as np
        count = 0
        days_to_threshold = 0
        if self.last_tmid_err is not None:  # check for timing error available
            # if available
            err_tot = float(self.last_tmid_err)
            if err_tot < threshold/24/60:  # check we are starting below threshold
                while err_tot < threshold/24/60:  # loop while below threshold
                    count += 1  # count epochs
                    # calculate next error
                    err_tot = np.sqrt(
                        float(self.last_tmid_err) * float(self.last_tmid_err) + count * count * float(
                            self.period_err) * float(self.period_err))
                days_to_threshold = count * float(self.period)  # convert epochs to days
            self.expiry = self.last_tmid + days_to_threshold  # add days to observation date
            #self.current_err = err_tot*24*60  # calculate current error in minutes
        else:  # no timing error available
            # set expiry and error to always get selected
            self.expiry = 0
            #self.current_err = 100000

    def check_if_required(self, date):
        import julian
        date_jd = julian.to_jd(date, fmt='jd') - 2400000  # convert date to JD
        # check for expiry
        if date_jd > self.expiry:
            return True
        else:
            return False

    def transit_forecast(self, start, end, telescopes):
        """
        Forecasts visible transits for the Target within the set dates at the Telescopes provided
        :param start: Start date of the window: datetime
        :param end: End date of the window: datetime
        :param telescopes: List of Telescope objects to be checked for visibility
        :return: List of visible Transits each marked with where they should be observed from
        """
        import julian
        from datetime import datetime, timedelta
        import transit
        import copy
        # check dates are in correct format
        if type(start) != datetime:
            start = julian.from_jd(start + 2400000, fmt='jd')
        if type(end) != datetime:
            end = julian.from_jd(end + 2400000, fmt='jd')

        # convert variables to the correct format
        current_ephemeris = julian.from_jd(self.last_tmid + 2400000, fmt='jd')
        period = timedelta(days=self.period)
        epoch = int(self.last_epoch)

        visible_transits = []
        while current_ephemeris < end:  # count towards the end of the window
            # iterate ephemeris and epoch
            current_ephemeris += period
            epoch += 1
            if start < current_ephemeris < end:  # check transit is in the future
                # create new Transit object filled with the required information, including the new ephemeris and epoch
                candidate = transit.Transit().init_for_forecast(vars(self), current_ephemeris, epoch)
                candidate.check_transit_visibility(telescopes)  # check visibility against telescopes
                if len(candidate.telescope) == 1:  # visible from single site
                    candidate.telescope = candidate.telescope[0]  # extract single value from array
                    visible_transits.append(candidate)  # add to list
                elif len(candidate.telescope) > 1:  # visible from multiple sites
                    for site in candidate.telescope:  # loop for sites
                        candidate_copy = copy.deepcopy(candidate)  # duplicate Transit object for each site
                        candidate_copy.telescope = site
                        visible_transits.append(candidate_copy)  # add a Transit object for each site to list

        return visible_transits

    def period_fit(self):
        import numpy as np

        epochs = []
        tmids = []
        weights = []

        for ob in self.observations:
            epochs.append(ob[0])
            tmids.append(ob[1])
            weights.append(1/ob[2])

        try:
            if len(epochs) > 3:
                # run fit and extract results
                poly_both = np.polyfit(epochs, tmids, 1, cov=True, w=weights)

                poly, cov = poly_both[0], poly_both[1]
                fit_period = poly[0]
                fit_period_err = np.sqrt(cov[0][0])  # calculate error

                self.period = fit_period
                self.period_err = fit_period_err

        except ValueError:
            pass
        except np.linalg.LinAlgError:
            pass
        except TypeError:
            pass





