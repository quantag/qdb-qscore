from qiskit_ibm_runtime import QiskitRuntimeService

token = ""
service = QiskitRuntimeService.save_account(
    token=token, # Your token is confidential.
    # Do not share your key in public code.
    instance="one", # Optionally specify the instance to use.
#    plans_preference="['plan-type1', 'plan-type2']", # Optionally set the types of plans to prioritize.  This is ignored if the instance is specified.
#    region="<region>", # Optionally set the region to prioritize. This is ignored if the instance is specified.
    name="myacc", # Optionally name this set of account credentials.
    set_as_default=True, # Optionally set these as your default credentials.
    overwrite=True
  )

 
