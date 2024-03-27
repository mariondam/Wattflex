'''
Example: optimal residential battery control based on EPEX day-ahead prices
'''
import pandas as pd
from battery import Battery
from epex_optimizer import EpexOptimizer


# Example data: Dutch EPEX day-ahead prices on 8 Nov 2022 with simulated household data 
prices = [0.04264, 0.02996, 0.0277, 0.02621, 0.03096, 0.03425, 
        0.068, 0.12827, 0.13552, 0.1001, 0.0814, 0.07927, 
        0.07535, 0.09123, 0.09346, 0.12103, 0.12067, 0.13951, 
        0.15773, 0.126, 0.118, 0.1217, 0.112, 0.098]
electricity_usage = [0.15, 0.12, 0.12, 0.15, 0.12, 0.14, 
                0.13, 0.12, 0.16, 0.15, 0.1, 0.45, 
                0.18, 0.01, 0.01, 0.06, 0.2, 0.71, 
                0.19, 0.29, 0.26, 0.25, 0.27, 0.21]
electricity_feedin = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 
                0.31, 0.49, 0.20, 0.01, 0.0, 0.0, 
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

df = pd.DataFrame({'electricity_usage': electricity_usage, 'electricity_feedin': electricity_feedin, 'price_euro_per_kwh': prices})

# Specify battery
battery_size = 5 #kWh
min_soc = 0.15
max_soc = 0.9
max_discharge_speed = 3.68 # kW
max_charge_speed = 2.5 #kW
efficiency = 0.9
battery = Battery(battery_size, min_soc, max_soc, max_discharge_speed, max_charge_speed, efficiency)

# Set start SoC and desired end SoC
start_soc = 0.15
end_soc = 0.15

# Set cutoff: minimal required yield per cycle (cycle = charge to max_soc, discharge to min_soc)
cutoff = 0.2

# Set taxes (VAT and electricity tax)
tax_rate = 0.21  
tax_per_kwh = 0.15  

allow_grid_discharge = True
allow_grid_charge = True
interval = 'hour'

# With the do_print option for each time period the actions, SoC and price is printed
params = [df, battery, start_soc, end_soc, tax_rate, tax_per_kwh, allow_grid_discharge, allow_grid_charge]

opt = EpexOptimizer(*params, interval = interval, cutoff = cutoff)
opt.LP_optimize()
daily_yield, orig_cost = opt.compute_yield(do_print = False)

# Get the amount to charge/discharge per hour (as list, in kWh)
charges = opt.get_charges()
discharges = opt.get_discharges()

# compute nr_cycles (battery starts and ends empty)
nr_cycles = sum(charges) / (battery.battery_size * (battery.max_soc - battery.min_soc))
print(f'With a minimal required yield per cycle of €{cutoff}, the yield of the battery for this day is €{round(daily_yield,2)}, using {round(nr_cycles,2)} cycles')


total_grid_charge = sum(opt.get_grid_charges())
total_grid_discharge = sum(opt.get_grid_discharges())
total_solar_charge = sum(opt.get_solar_charges())
total_selfuse_discharge = sum(opt.get_selfuse_discharges())

print(f'{round(total_grid_charge,2)} kWh is charged from the grid')
print(f'{round(total_solar_charge,2)} kWh is charged from the solar surplus')
print(f'{round(total_grid_discharge,2)} kWh is discharged to the grid')
print(f'{round(total_selfuse_discharge,2)} kWh is discharged for self-use')