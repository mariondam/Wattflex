import numpy as np
from scipy.optimize import linprog
import math

class EpexOptimizerNM():
    """A class used to optimize control of a residential battery on EPEX day-ahead 
    prices using linear programming, applicable under Dutch net metering (NM) arrangement
    
    ... 
    Attributes
    ----------
    
    prices : list
        List of prices of period to optimize
    battery : Battery
        A battery with fixed properties from the Battery-class
    start_soc : float, optional
        Starting State of Charge of the battery, default 0. 
    cutoff : float, optional
        Cutoff of minimal required yield, default 0 (use every price difference as opportunity for the battery)

    Methods
    ---------
    set_socs(end_soc):
        Set the start_ and end_soc as follows: the last end_soc is set as the new start_soc, the new end_soc 
        is set to the end_soc passed as parameter.
    LP_optimize(): 
        Runs the LP-optimization
    get_grid_discharges(), get_selfuse_discharges(), get_grid_charges(), get_solar_charges():
        If LP_optimize() ran successfully, the above functions will return a list of length T with the 
        (dis)charge per hour in kWh. Otherwise, a list of 0's of length T is returned. 
    get_charges(), get_discharges():
        If LP_optimize() ran successfully, these return a list of length T with the total charges and 
        discharges per hour. Otherwise, a list of 0's of length T is returned.
    get_socs():
        If LP_optimize() ran successfully, returns a list of soc's throughout the hours. 
        Otherwise, a list of 0's of length T is returned.
    compute_yield(do_print = False):
        Compute the _yield of applying the battery as follows from LP_optimize() compared to original usage/return. 
        When do_print = True, information per hour is printed.


    """

    def __init__(self, prices, battery, start_soc = 0, end_soc = 0, cutoff = 0):
        self.prices = prices
        self.battery = battery
        self.cutoff = cutoff
        self.start_soc = start_soc
        self.end_soc = end_soc
        self.T = len(prices)  # number of periods considered
        self.opt = None
        self.yield_in_period = None
        self.M = 10000000


    def LP_optimize(self):
        # order in objective: ([xt, yt, st]) where:
        # xt: total netto discharge (corrected for efficiency), 
        # yt: total charge
        # st: socs
        # zt: boolean
        effective_battery_size = (self.battery.max_soc - self.battery.min_soc) * self.battery.battery_size
        obj =  np.array([- p + (self.cutoff / (effective_battery_size * self.battery.efficiency) ) for p in self.prices ]
                         + [p for p in self.prices] 
                         + [0] * 2 * self.T)

        lhs_ineq, rhs_ineq = self._create_ineqality_constraints()
        lhs_eq, rhs_eq = self._create_equality_constraints()

        # Make sure zt is boolean
        integrality = np.array([0] * 3 * self.T + [1] * self.T)

        self.opt = linprog(c=obj, A_ub=lhs_ineq, b_ub=rhs_ineq, A_eq = lhs_eq, b_eq = rhs_eq, integrality = integrality)
        
        if not self.opt.success:
            warn_color = '\033[93m'
            end_warn_color = '\033[0m'
            print(warn_color + '\n' + self.opt.message + '\n' + end_warn_color)

            # set it to None so it does not raise an exception
            # (note: when opt = None, compute_yield returns 0)
            self.opt = None
            #raise Exception('Problem not optimized!')


    def get_charges(self):
        if not self.opt: 
            return [0 for _ in range(self.T)]
        return [round(c, 4) for c in list(self.opt.x[1 * self.T: 2 * self.T])]

    def get_discharges(self):
        if not self.opt: 
            return [0 for _ in range(self.T)]
        return [round(abs(dc), 4) for dc in list(self.opt.x[0 * self.T: 1 * self.T])]


    def get_socs(self):
        if not self.opt: 
            return [0 for _ in range(self.T)]
        
        socs = list(self.opt.x[2 * self.T : 3 * self.T])
        # First soc can be anything since this is not part of optimization. 
        # Manually set it to start_soc.
        socs[0] = self.start_soc
        return socs


    def compute_yield(self, do_print = False):
        if not self.opt: 
            return 0

        discharge = self.get_discharges()
        charge = self.get_charges()
        soc = self.get_socs()

        yield_in_period = 0
        for i in range(self.T):
            if do_print:
                print(f'discharge: {round(discharge[i],2)}, charge: {round(charge[i], 2)}, soc: {round(soc[i],2)}, price: {self.prices[i]}')

            dis = discharge[i] * self.prices[i]
            cha = charge[i] * self.prices[i]
            
            yield_in_period += dis - cha

        self.yield_in_period = yield_in_period

        if do_print:
            print(f'Yield: {round(self.yield_in_period,4)}')

        return self.yield_in_period


    def _create_ineqality_constraints(self):
        # INEQUALITY CONSTRAINTS
        lhs_ineq = []
        rhs_ineq = []

        # add constraint: x_t  <= max_discharge_power for all t
        for i in range(self.T):
            tmp_list = [0] * 4 * self.T
            tmp_list[i + 0 * self.T] = 1
            lhs_ineq.append(tmp_list)
            rhs_ineq.append( self.battery.max_discharge_power)
      
    
        # add constraint: y_t <= max_charge_power for all t
        for i in range(self.T):
            tmp_list = [0] * 4 * self.T
            tmp_list[i + 1 * self.T] = 1
            lhs_ineq.append(tmp_list)
            rhs_ineq.append(self.battery.max_charge_power)


        # add constraint soc <= max_soc
        for i in range(self.T):
            tmp_list = [0] * 4 * self.T
            tmp_list[2 * self.T + i] = 1
            lhs_ineq.append(tmp_list)
            rhs_ineq.append(self.battery.max_soc)

        # add constraint: soc >= min_soc (-soc <= -min_soc)
        for i in range(self.T):
            tmp_list = [0] * 4 * self.T
            tmp_list[2 * self.T + i] = -1
            lhs_ineq.append(tmp_list)
            rhs_ineq.append(-self.battery.min_soc)


        # add constraint x_t <= M(1-z) 
        # (prevent charging and discharging in the same hour if price is 0)
        # z is now a boolean: if discharge, then z = 0, else z = 1
        for i in range(self.T):
            tmp_list = [0] * 4 * self.T
            tmp_list[i + 3 * self.T] = self.M
            tmp_list[i] = 1
            lhs_ineq.append(tmp_list)
            rhs_ineq.append(self.M)

        # add constraint y_t <= M * z
        for i in range(self.T):
            tmp_list = [0] * 4 * self.T
            tmp_list[i + 3 * self.T] = - self.M
            tmp_list[i + 1 * self.T] = 1
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
            tmp_list = [0] * 4 * self.T
            if i == 0:
                tmp_list[2 * self.T + i + 1] = 1
                tmp_list[0 * self.T + i] = 1  / (self.battery.battery_size * self.battery.efficiency)
                tmp_list[1 * self.T + i] = -1 / self.battery.battery_size
                rhs = self.start_soc
            elif i < self.T - 1:
                tmp_list[2 * self.T + i] = -1
                tmp_list[2 * self.T + i + 1] = 1
                tmp_list[0 * self.T + i] = 1  / (self.battery.battery_size * self.battery.efficiency)
                tmp_list[1 * self.T + i] = -1 / self.battery.battery_size
                rhs = 0
            else:
                tmp_list[2 * self.T + i] = -1
                tmp_list[0 * self.T + i] = 1  / (self.battery.battery_size * self.battery.efficiency)
                tmp_list[1 * self.T + i] = -1 / self.battery.battery_size  
                rhs = - self.end_soc

            lhs_eq.append(tmp_list)
            rhs_eq.append(rhs)

        #  to np arrays
        lhs_eq = np.array(lhs_eq)
        rhs_eq = np.array(rhs_eq)

        return lhs_eq, rhs_eq