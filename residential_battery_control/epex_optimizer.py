import numpy as np
from scipy.optimize import linprog
import math

class EpexOptimizer():
    """A class used to optimize a battery on EPEX day-ahead prices, 
    grid charge/discharge, solar charge and selfuse discharge
    
    ... 
    Attributes
    ----------
    
    df : pd.DataFrame
        dataframe for the household (hh) which contains the following columns for the period
        to optimize (of length T): price_euro_per_kwh, electricity_usage, electricity_feedin.
    battery : Battery
        A battery with fixed properties from the Battery-class that is used in this household.
    start_soc : float, optional
        Starting State of Charge of the battery, default 0. 
    tax_rate : float, optional
        Tax rate (VAT) as a number between 0 and 1. So, 0.21 means a tax of 21% is added to the price. Default 0.
    tax_per_kwh : float, optional
        Tax (or other rates) that is fixed per kWh, such as energy tax. This must already include the 
        VAT defined above if applicable. Default 0. 
    allow_grid_discharge : bool, optional
        Whether or not to allow discharges to the grid. Default True.
    allow_grid_charge : bool, optional
        Whether or not to allow charge from the grid. Default True.
    cutoff : float, optional
        Cutoff of minimal required yield, default 0 (use every price difference as opportunity for the battery)
    interval : string, optional
        Options: hour, quarter. If quarter, then only 0.25 * max_charge_power and 0.25 * max_discharge_power 
        are allowed (as results are in kWh). Defaults to hour.

    Methods
    ---------
    LP_optimize(): 
        Runs the LP-optimization
    get_grid_discharges(), get_selfuse_discharges(), get_grid_charges(), get_solar_charges():
        If LP_optimize() ran successfully, the above functions will return a list of length T with the 
        (dis)charge per period in kWh. Otherwise, a list of 0's of length T is returned. 
    get_charges(), get_discharges():
        If LP_optimize() ran successfully, these return a list of length T with the total charges and 
        discharges per period as a fraction of max_charge_speed or max_discharge_speed respectively. Otherwise, 
        a list of 0's of length T is returned.
    get_socs():
        If LP_optimize() ran successfully, returns a list of soc's throughout the periods. 
        Otherwise, a list of 0's of length T is returned.
    compute_yield(do_print = False):
        Compute the yield of applying the battery as follows from LP_optimize() compared to original usage/feedin. 
        When do_print = True, information on the charging/discharging per period is printed.
    """

    def __init__(self, df, battery, start_soc = 0, end_soc = 0, tax_rate = 0, tax_per_kwh = 0, 
        allow_grid_discharge = True, allow_grid_charge = True, cutoff = 0, interval = 'hour'):
        
        self.df = df
        self.battery = battery
        self.start_soc = start_soc
        self.end_soc = end_soc
        self.tax_per_kwh = tax_per_kwh  # note: must INCLUDE VAT if applicable
        self.tax_rate = tax_rate
        self.allow_grid_discharge = allow_grid_discharge
        self.allow_grid_charge = allow_grid_charge
        self.cutoff = cutoff
        self.interval = interval
        if self.interval == 'hour':
            self.interval_fraction = 1
        elif self.interval == 'quarter':
            self.interval_fraction = 0.25
        else: 
            print(f'Invalid interval entered, assuming hour (valid: hour, quarter, received: {self.interval})')

        self.M = 1000 # big M
        self.opt = None
        self.yield_in_period = None

        self._set_period()


    def _set_period(self):
        el_use = list(self.df['electricity_usage'])
        el_feedin = list(self.df['electricity_feedin'])
        prices = list(self.df['price_euro_per_kwh'])        

        # replace any nans with 0
        el_use = [x if not math.isnan(x) else 0 for x in el_use]
        el_feedin = [x if not math.isnan(x) else 0 for x in el_feedin]

        self.electricity_use = el_use
        self.electricity_feedin = el_feedin
        self.prices = prices
        self.prices_tax = [p * (1 + self.tax_rate) + self.tax_per_kwh for p in self.prices]

    def LP_optimize(self):
        self.T = len(self.prices)

        neg_prices = [- p for p in self.prices]
        neg_prices_tax = [- p for p in self.prices_tax]

        # order in objective: ([gxt, zxt, gyt, zyt, xt, yt, st]) where:
        # gxt: grid discharges (kWh) 
        # zxt: selfuse discharges (kWh) 
        # gyt: grid charges (kWh)
        # zyt: solar charges (kWh), 
        # xt: total discharges (fraction of max_discharge_speed), 
        # yt: charges (fraction of max_charge_speed)
        # st: socs
        # Boolean whether there is discharge or not
        effective_battery_size = (self.battery.max_soc - self.battery.min_soc) * self.battery.battery_size
        obj =  np.array([*neg_prices, 
                        *neg_prices_tax, 
                        *self.prices_tax, 
                        *self.prices ] 
                        + [self.cutoff / (effective_battery_size * self.battery.efficiency)] * self.T 
                        + [0] * 3 * self.T)

        lhs_ineq, rhs_ineq = self._create_ineqality_constraints()
        lhs_eq, rhs_eq = self._create_equality_constraints()

        # Make sure zt is boolean
        integrality = np.array([0] * 7 * self.T + [1] * self.T)

        self.opt = linprog(c=obj, A_ub=lhs_ineq, b_ub=rhs_ineq, A_eq = lhs_eq, b_eq = rhs_eq, integrality = integrality)
        
        if not self.opt.success:
            warn_color = '\033[93m'
            end_warn_color = '\033[0m'
            #print(warn_color + '\n' + self.opt.message + '\n' + end_warn_color)

            # set it to None so it does not raise an exception
            # (note: when opt = None, compute_yield returns 0)
            self.opt = None
            #raise Exception('Problem not optimized!')


    def get_grid_discharges(self):
        if not self.opt: 
            return [0 for _ in range(self.T)]
        return list(self.opt.x[0: self.T])

    def get_selfuse_discharges(self):
        if not self.opt: 
            return [0 for _ in range(self.T)]
        return list(self.opt.x[self.T: 2 * self.T])

    def get_grid_charges(self):
        if not self.opt: 
            return [0 for _ in range(self.T)]
        return list(self.opt.x[2 * self.T: 3 * self.T])

    def get_solar_charges(self):
        if not self.opt: 
            return [0 for _ in range(self.T)]
        return list(self.opt.x[3 * self.T: 4 * self.T])

    def get_charges(self):
        if not self.opt: 
            return [0 for _ in range(self.T)]
        return list(self.opt.x[5 * self.T: 6 * self.T])

    def get_discharges(self):
        if not self.opt: 
            return [0 for _ in range(self.T)]
        return list(self.opt.x[4 * self.T: 5 * self.T])

    def get_socs(self):
        if not self.opt: 
            return [0 for _ in range(self.T)]
        # First soc can be anything since this is not part of optimization. 
        # Manually set it to start_soc.
        socs = list(self.opt.x[6 * self.T : 7 * self.T])
        socs[0] = self.start_soc
        return socs

    def compute_yield(self, do_print = False):
        if not self.opt: 
            orig_cost = 0
            for i in range(self.T):
                orig_cost += round(-self.electricity_feedin[i] * self.prices[i] + self.electricity_use[i] * self.prices_tax[i], 6)
            return 0, orig_cost

        grid_discharge = self.get_grid_discharges()
        selfuse_discharge = self.get_selfuse_discharges()
        grid_charge = self.get_grid_charges()
        solar_charge = self.get_solar_charges()
        discharge = self.get_discharges()
        charge = self.get_charges()
        soc = self.get_socs()

        extra_cost = 0
        orig_cost = 0
        for i in range(self.T):
            if do_print:
                print(f'orig u,r: {round(self.electricity_use[i],2), round(self.electricity_feedin[i],2)}, grid_d: {round(grid_discharge[i],2)}, selfuse_d: {round(selfuse_discharge[i], 2)}, grid_c: {round(grid_charge[i],2)}, solar_c: {round(solar_charge[i], 2)}, soc: {round(soc[i],2)}, price: {round(self.prices[i], 3)}, taxpr: {round(self.prices_tax[i],3)}')

            extra_cost += grid_charge[i] * self.prices_tax[i] + solar_charge[i] * self.prices[i] - \
                    selfuse_discharge[i] * self.prices_tax[i] - grid_discharge[i] * self.prices[i]

            orig_cost += round(-self.electricity_feedin[i] * self.prices[i] + self.electricity_use[i] * self.prices_tax[i], 6)
            
        self.yield_in_period = - extra_cost

        if do_print:
            print(f'Original cost: {round(orig_cost, 2)}')
            print(f'Yield: {round(self.yield_in_period,2)}')

        total_cost = orig_cost + extra_cost

        return self.yield_in_period, total_cost


    def _create_ineqality_constraints(self):
        # INEQUALITY CONSTRAINTS
        lhs_ineq = []
        rhs_ineq = []

        # add constraint: soc <= max_soc
        for i in range(self.T):
            tmp_list = [0] * 8 * self.T
            tmp_list[6 * self.T + i] = 1
            lhs_ineq.append(tmp_list)
            rhs_ineq.append(self.battery.max_soc)

        # add constraint: soc >= min_soc (-soc <= -min_soc)
        for i in range(self.T):
            tmp_list = [0] * 8 * self.T
            tmp_list[6 * self.T + i] = -1
            lhs_ineq.append(tmp_list)
            rhs_ineq.append(-self.battery.min_soc)

        # add inequality constraint: zyt <= el_feedin
        for i in range(self.T):
            tmp_list = [0] * 8 * self.T
            tmp_list[i + 3 * self.T] = 1
            lhs_ineq.append(tmp_list)
            rhs_ineq.append(self.electricity_feedin[i])   

        # add inequality constraint: zxt <= el_use
        for i in range(self.T):
            tmp_list = [0] * 8 * self.T
            tmp_list[i + self.T] = 1
            lhs_ineq.append(tmp_list)
            rhs_ineq.append(self.electricity_use[i])  

        # add inequality constraint: xt <= self.interval_fraction * max_discharge_power
        for i in range(self.T):
            tmp_list = [0] * 8 * self.T
            tmp_list[i + 4 * self.T] = 1
            lhs_ineq.append(tmp_list)
            rhs_ineq.append(self.battery.max_discharge_power * self.interval_fraction)  

        # add inequality constraint: yt <= self.interval_fraction * max_charge_power
        for i in range(self.T):
            tmp_list = [0] * 8 * self.T
            tmp_list[i + 5 * self.T] = 1
            lhs_ineq.append(tmp_list)
            rhs_ineq.append(self.battery.max_charge_power * self.interval_fraction)  

        # add constraint x_t <= M(1-z)
        # (prevent charging and discharging in the same hour if price is 0)
        # z is now a boolean: if no discharge, then z = 1, if discharge, then z = 0
        for i in range(self.T):
            tmp_list = [0] * 8 * self.T
            tmp_list[i + 7 * self.T] = self.M
            tmp_list[i + 4 * self.T] = 1
            lhs_ineq.append(tmp_list)
            rhs_ineq.append(self.M)

        # add constraint y_t <= M * z
        for i in range(self.T):
            tmp_list = [0] * 8 * self.T
            tmp_list[i + 7 * self.T] = - self.M
            tmp_list[i + 5 * self.T] = 1
            lhs_ineq.append(tmp_list)
            rhs_ineq.append(0)
        
        # convert to np.array
        lhs_ineq = np.array(lhs_ineq)
        rhs_ineq = np.array(rhs_ineq)

        return lhs_ineq, rhs_ineq


    def _create_equality_constraints(self):
        # EQUALITY CONSTRAINTS 
        # add equality constraint: soc_t+1 - soc_t - x_t + y_t = 0
        # (derived from: battery soc = old_soc + charge - discharge)
        lhs_eq = []
        rhs_eq = []
        for i in range(self.T):
            tmp_list = [0] * 8 * self.T
            if i == 0:
                tmp_list[6 * self.T + i + 1] = 1
                tmp_list[4 * self.T + i] = 1  / (self.battery.battery_size * self.battery.efficiency)
                tmp_list[5 * self.T + i] = -1 / self.battery.battery_size 
                rhs = self.start_soc
            elif i < self.T - 1:
                tmp_list[6 * self.T + i] = -1
                tmp_list[6 * self.T + i + 1] = 1
                tmp_list[4 * self.T + i] = 1  / (self.battery.battery_size * self.battery.efficiency)
                tmp_list[5 * self.T + i] = -1 / self.battery.battery_size 
                rhs = 0
            else:
                tmp_list[6 * self.T + i] = -1
                tmp_list[4 * self.T + i] = 1  / (self.battery.battery_size * self.battery.efficiency)
                tmp_list[5 * self.T + i] = -1 / self.battery.battery_size
                rhs = - self.end_soc

            lhs_eq.append(tmp_list)
            rhs_eq.append(rhs)

        # add equality constraint: y_t = gyt + zyt
        for i in range(self.T):
            tmp_list = [0] * 8 * self.T
            tmp_list[i + 2 * self.T] = 1
            tmp_list[i + 3 * self.T] = 1
            tmp_list[i + 5 * self.T] = - 1 
            lhs_eq.append(tmp_list)
            rhs_eq.append(0)    

        # add equality constraint: x_t = gxt + zxt
        for i in range(self.T):
            tmp_list = [0] * 8 * self.T
            tmp_list[i] = 1
            tmp_list[i + self.T] = 1
            tmp_list[i + 4 * self.T] = - 1
            lhs_eq.append(tmp_list)
            rhs_eq.append(0)    

        
        if not self.allow_grid_discharge:
            # add constraint sum(gx_t) = 0
            tmp_list = [0] * 8 * self.T
            for i in range(self.T):
                tmp_list[i] = 1
            lhs_eq.append(tmp_list)
            rhs_eq.append(0)

        if not self.allow_grid_charge:
            # add constraint sum(gy_t) = 0
            tmp_list = [0] * 8 * self.T
            for i in range(self.T):
                tmp_list[i + 2 * self.T] = 1
            lhs_eq.append(tmp_list)
            rhs_eq.append(0)

        #  to np arrays
        lhs_eq = np.array(lhs_eq)
        rhs_eq = np.array(rhs_eq)

        return lhs_eq, rhs_eq