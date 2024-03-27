'''
Example: optimal residential battery control based on EPEX day-ahead prices
under the Dutch Net Metering arrangement
'''

from battery import Battery
from epex_optimizer_nm import EpexOptimizerNM


# Example prices: Dutch EPEX day-ahead prices on 8 Nov 2022
prices = [0.04264, 0.02996, 0.0277, 0.02621, 0.03096, 0.03425, 
        0.068, 0.12827, 0.13552, 0.1001, 0.0814, 0.07927, 
        0.07535, 0.09123, 0.09346, 0.12103, 0.12067, 0.13951, 
        0.15773, 0.126, 0.118, 0.1217, 0.112, 0.098]

# Specify battery
battery_size = 5 #kWh
min_soc = 0.15
max_soc = 0.9
max_discharge_speed = 3.68 # kW
max_charge_speed = 2.5 #kW
efficiency = 0.9
battery = Battery(battery_size, min_soc, max_soc,  max_discharge_speed, max_charge_speed, efficiency)

# Set start SoC and desired end SoC
start_soc = 0.15
end_soc = 0.15

# Set cutoff: minimal required yield per cycle (cycle = charge to max_soc, discharge to min_soc)
cutoff = 0.0

# Run LP-optimization on epex-prices
opt = EpexOptimizerNM(prices, battery, start_soc, end_soc, cutoff)
opt.LP_optimize()
# With the do_print option for each time period the actions, SoC and price is printed
daily_yield = opt.compute_yield(do_print = False)

# Get the amount to charge/discharge per hour (as list, in kWh)
charges = opt.get_charges()
discharges = opt.get_discharges()

# compute nr_cycles (battery starts and ends empty)
nr_cycles = sum(charges) / (battery.battery_size * (battery.max_soc - battery.min_soc))
print(f'With a minimal required yield per cycle of €{cutoff}, the yield for this day is €{round(daily_yield,2)}, using {nr_cycles} cycles')


# Try different cutoff, gives different results
cutoff = 0.20

# Run LP-optimization on epex-prices
opt = EpexOptimizerNM(prices, battery, start_soc, cutoff)
opt.set_socs(end_soc)
opt.LP_optimize()
daily_yield = opt.compute_yield(do_print = False)

charges = opt.get_charges()
nr_cycles = sum(charges) / (battery.battery_size * (battery.max_soc - battery.min_soc))
print(f'With a minimal required yield per cycle of €{cutoff}, the yield of the battery for this day is €{round(daily_yield,2)}, using {nr_cycles} cycles')