PARAMETER_RANGES = {
  "delay":(0.0, 180.0),
  "carbon":(0.0,300.0),
  "technical_risk":(0.0,1.0),
  "crew_compliance":(0.0,1.0),
  "cancellation_impact":(0.0,1.0)
}

def normalize_value(
    value: float,
    minimum:float,
    maximum:float
) ->float:
  if maximum <=minimum:
    raise ValueError("Maximum value must be greater that minimum value for normalization")
  clamped_value = max(minimum , min(value, maximum))
  normalized_value = ((clamped_value - minimum) / (maximum - minimum)
  )

  return round(normalized_value , 3)

def normalize_parameters(parameters: dict) -> dict:
  normalized_parameters = {}
  for parameter_name, value in parameters.items():
    if parameter_name not in PARAMETER_RANGES:
      raise ValueError(f"No normalization range defined for: {parameter_name}")
    minimum, maximum = PARAMETER_RANGES[parameter_name]
    normalized_parameters[parameter_name] = normalize_value(value = value,
                                                            minimum = minimum,
                                                            maximum = maximum)
  return normalized_parameters
