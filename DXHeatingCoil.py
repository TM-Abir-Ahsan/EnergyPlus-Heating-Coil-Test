import psychrolib
# Set the unit system, for example to SI (can be either psychrolib.SI or psychrolib.IP)
psychrolib.SetUnitSystem(psychrolib.SI)

def TotCapTempModFac(Tdb):
    """Calculate Total Capacity Temperature Modification Factor using polynomial coefficients."""
    a, b, c, d = 0.758746, 0.027626, 0.000148716, 0.0000034992
    return a + b * Tdb + c * Tdb ** 2 + d * Tdb ** 3

def TotCapFlowModFac(FF):
    """Calculate Total Capacity Flow Modification Factor using polynomial coefficients."""
    a, b, c, d = 0.84, 0.16, 0.0, 0.0
    return a + b * FF + c * FF ** 2 + d * FF ** 3

def EERTempModFac(Tdb):
    """Calculate EER Temperature Modification Factor."""
    a, b, c, d = 1.19248, -0.0300438, 0.00103745, -0.000023328
    return a + b * Tdb + c * Tdb ** 2 + d * Tdb ** 3

def EERFlowModFac(FF):
    """Calculate EER Flow Modification Factor."""
    a, b, c, d = 1.3824, -0.4336, 0.0512, 0.0
    return a + b * FF + c * FF ** 2 + d * FF ** 3

def PLF_curve(PLR):
    """Calculate Part Load Factor."""
    return 0.85 + 0.15 * PLR

def DefrostEIRTempModFac(Twbi,Tdb):
    """Calculate Defrost EIR Temperature Modification Factor."""
    a, b, c, d, e, f = 1,0,0,0,0,0
    return a + b * Twbi + c * Twbi ** 2 + d * Tdb + e * Tdb ** 2 +  f * Twbi * Tdb

def DefrostCalc(Tdbo, Twbo, DemandDefrost="OnDemand", tfrac_defrost=None):
    """Calculate Defrost Energy Input Ratio.
    
    Args:
        Tdbo: Outdoor dry bulb temperature
        Twbi: Outdoor wet bulb temperature
        DemandDefrost: Either "OnDemand" or "Timed" (default: "OnDemand")
        tfrac_defrost: Defrost time fraction — REQUIRED only if DemandDefrost="Timed"

    Returns:
        Heating_Capacity_Multiplier: Multiplier for heating capacity during defrost
    """

    OutdoorCoilT = 0.82 * Tdbo - 8.589
    OutdoorPress = 98600  # Standard atmospheric pressure in Pa
    OutdoorHumRat = psychrolib.GetHumRatioFromTWetBulb(Tdbo, Twbo, OutdoorPress)
    OutdoorCoildw = max(1e-6, OutdoorHumRat - psychrolib.GetSatHumRatio(OutdoorCoilT, OutdoorPress))

    if DemandDefrost == "OnDemand":
        tfrac_defrost = 1 / (1 + (0.01446/OutdoorCoildw))
        Heating_Capacity_Multiplier = 0.875 * (1 - tfrac_defrost)
        Input_Power_Multiplier = 0.954 * (1 - tfrac_defrost)
    else:  # Timed defrost
        # Use user-provided fraction, or fall back to common default
        if tfrac_defrost is None:
            tfrac_defrost = 0.058333  # Common EnergyPlus default (≈3.5 min defrost per hour)
        # Else use the provided value (e.g., 0.033 as in your original)
        Heating_Capacity_Multiplier = 0.909 - 107.33 * OutdoorCoildw
        Input_Power_Multiplier = 0.9 - 36.45 * OutdoorCoildw

    return Heating_Capacity_Multiplier, Input_Power_Multiplier, tfrac_defrost


# Changing parameters
OAT = 2.7 # Outdoor Air Temperature in C
Outdoor_WBT = 1.332824959 # Outdoor Wet-Bulb Temperature in C
Indoor_WBT = 12.1110695 # Indoor Wet-Bulb Temperature in C
Delivered_Load = 175901.2156 # in W


# Non-changing parameters
OAT_max_defrost = 5 # Maximum Outdoor Air Temperature for Defrost Operation in C
Q_total_rated = 14333.9065 # Rated total capacity in J
COP_rated = 3.8377982946518


if OAT <= OAT_max_defrost:
    Input_Power_Multiplier = DefrostCalc(OAT, Outdoor_WBT, DemandDefrost="OnDemand")[1]
    Q_total = Q_total_rated * TotCapTempModFac(OAT) * TotCapFlowModFac(1) * DefrostCalc(OAT, Outdoor_WBT, DemandDefrost="OnDemand")[0]   # W
    Q_defrost = 0.01 * DefrostCalc(OAT, Outdoor_WBT, DemandDefrost="OnDemand")[2] * (7.222-OAT) * (Q_total_rated/1.01667)  # W
    PLR = Delivered_Load / (Q_total*60) # -
    PLR = min(1.0, PLR + Q_defrost/Q_total) # -
    PLF = PLF_curve(PLR) # -
    RTF = min(1, PLR/PLF) # -
    P_defrost = DefrostEIRTempModFac(Indoor_WBT, OAT) * (Q_total_rated / 1.01667) * DefrostCalc(OAT, Outdoor_WBT, DemandDefrost="OnDemand")[2] * RTF  # W
    P_heating = 1/COP_rated * Q_total * EERTempModFac(OAT) * EERFlowModFac(1) * DefrostCalc(OAT, Outdoor_WBT, DemandDefrost="OnDemand")[1] * RTF # W
else:
    Input_Power_Multiplier = 1      # set to unity for no defrost operation
    Heating_capacity_multiplier = 1 # set to unity for no defrost operation
    Q_total = Q_total_rated * TotCapTempModFac(OAT) * TotCapFlowModFac(1) * Heating_capacity_multiplier   # W
    PLR = Delivered_Load / (Q_total*60) # -
    PLF = PLF_curve(PLR) # -
    RTF = min(1, PLR/PLF) # -
    P_heating = 1/COP_rated * Q_total * EERTempModFac(OAT) * EERFlowModFac(1) * Input_Power_Multiplier * RTF # W
    P_defrost = 0 # W

print(f"Total heating power: {P_heating * 60} J")

print(f"Defrost power: {P_defrost * 60} J")
