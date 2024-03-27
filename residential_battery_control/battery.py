class Battery():
    """A class that sets the properties of a battery
    
    ... 
    Attributes
    ----------
    battery_size : float, optional
        Size of the battery (in kWh), default 1
    min_soc, max_soc : float, optional
        Minimal and maximal SoC of the battery. min_soc and max_soc must be between 
        0 and 1, otherwise they are set to 0 and 1 respectively. Defaults: 0, 1.
    max_discharge_power, max_charge_power: float, optional
        Maximal discharge and charge power (in kW), defaults 1
    efficiency : float, optional
        Efficiency of the battery. An efficiency of 0.9 means that for every 1 kWh in the battery, 
        only 0.9 kWh can be discharged. Default 1.

    """

    def __init__(self, battery_size = 1, min_soc = 0, max_soc = 1, max_discharge_power = 1, max_charge_power = 1, 
        efficiency = 1):

        self.min_soc = min_soc if 0 <= min_soc < 1 else 0 # must be in [0,1)
        self.max_soc = max_soc if 0 < max_soc <= 1 else 1 # must be in (0,1]

        self.battery_size = battery_size  # in kWh
        self.max_discharge_power = max_discharge_power   # in kW
        self.max_charge_power = max_charge_power    # in kW
        self.discharge_ratio = round(self.max_discharge_power / self.battery_size, 3) 
        self.charge_ratio = round(self.max_charge_power / self.battery_size, 3) 
        self.efficiency = efficiency

    