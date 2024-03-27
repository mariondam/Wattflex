# Contents - residential battery control on day-ahead prices

This folder contains code for optimization of control for residential Battery Energy Storage Systems (BESS) on day-ahead prices, created as part of the [Wattflex](https://projecten.topsectorenergie.nl/projecten/wattflex-ontwikkeling-van-cooperatieve-aggregator-diensten-36292) project. 

In the Netherlands, households can opt for a dynamic contract, where electricity prices vary hourly as they are based on the EPEX day-ahead prices. For Wattflex, optimal control as well as profitability of a residential battery based on these day-ahead prices was studied. 

There are two situations distinguished: 
 1. The specific situation of **optimal control of a residential battery in the Netherlands under the current Dutch Net Metering (NM) arrangement** (salderingsregeling). In this situation, only the day-ahead prices themselves must be considered to determine optimal control. 
 2. The general situation of **optimal *deterministic* control of a residential battery** without NM. This situation is applicable for any household that can opt for an energy contract based on hourly varying day-ahead prices, where no net metering scheme is present. In this case, electricity usage from the grid is charged based on the day-ahead price including taxes and feed-in to the grid yields the day-ahead price that is applicable at the time of feed-in. The resulting optimal control cannot be directly used for day-ahead residential battery control, as it requires data on actual usage and feed-in of a specific household, which is not available a day in advance (although it could be predicted). However, this can be used to study profitability of residential BESS for different households. 


## Minimal required yield per cycle
Part of both control algorithms is the choice of a *cutoff*-value for the minimal required yield per cycle. The default value is 0, meaning that the battery will use any non-negative price difference to charge and discharge. When this value is for example set to 0.2 (in €), this means that the battery will only act on price differences such that the yield is at least €0.20. This leads to less cycles, but to a higher average yield per cycle, thereby giving an opportunity to balance battery degradation and yield (an example is given in *example_epex_optimizer_nm.py*, and also discussed below). 

## 1: Residential BESS control with day-ahead prices under the Dutch NM arrangement
In *epex_optimizer_nm.py*, a class is defined that, given a battery and electricity prices, uses linear programming to determine optimal day-ahead control. An example usage is given in *example_epex_optimizer_nm.py*. Here, the Dutch EPEX-prices of 8 November 2022 (in € per kWh) are used as demonstration. 

Two cutoff-values for the minimal required yield per cycle are used. The result of the script is as follows:

```
With a minimal required yield per cycle of €0.0, the yield for this day is €0.6, using 2.0 cycles
With a minimal required yield per cycle of €0.2, the yield for this day is €0.43, using 1.0 cycles
```

## 2: Residential BESS control with day-ahead prices
In *epex_optimizer.py*, a class is defined that, given not only a battery and electricity prices, but also electricity usage from and feed-in to the grid from a household, uses linear programming to determine deterministic optimal day-ahead control. An example usage is given in *example_epex_optimizer.py*. 

The output of the example is as follows:
```
With a minimal required yield per cycle of €0.2, the yield for this day is €0.38, using 0.85 cycles
2.19 kWh is charged from the grid
1.0 kWh is charged from the solar surplus
0.0 kWh is discharged to the grid
2.87 kWh is discharged for self-use
```

Notes:
- The total charges in the example add up to 3.19 kWh, while the total discharge is 2.87 kWh, while the SoC at the end of the day is required to be equal to the SoC at the beginning of the day. This is due to the efficiency of the battery, which is set to 90% (0.9 * 3.19 = 2.87). 
- In the example, hourly data is used. For actual application, this resolution is too low, as in hourly energy consumption/feed-in data, short peaks in power are averaged out. This might lead to an overestimation of how much energy solar surplus can be charged into the battery, as well as how much energy can be discharged for self-use. 
- By setting *allow_grid_charge* and *allow_grid_discharge* both to False, the battery is controlled to optimize self-consumption. 
