class Observation:
    def __init__(self, transit):
        from datetime import timedelta
        self.target = transit.name
        self.center = transit.center
        if transit.ingress_visible:
            self.start = transit.ingress - timedelta(minutes=45)
        else:
            self.start = transit.ingress
        if transit.egress_visible:
            self.end = transit.egress + timedelta(minutes=45)
        else:
            self.end = transit.egress
        self.telescope = transit.telescope
        self.duration = self.end - self.start

        self.tmid = None
        self.tmid_err = None
        self.epoch = transit.epoch

    def generate_data(self):
        import julian
        from random import gauss
        new_tmid_exp = julian.to_jd(self.center, fmt='jd') - 2400000
        new_tmid = gauss(new_tmid_exp, 0.5 / 24 / 60)
        new_tmid_err = abs(gauss(0.5, 0.01) / 24 / 60)
        return self.target, self.epoch, new_tmid, new_tmid_err

    def flip_unfair_coin(self):
        """
        Determines the success of an observation by flipping a weighted coin
        :return: Success: boolean
        """
        import random
        chance = 0.6
        return True if random.random() < chance else False
        # return True
