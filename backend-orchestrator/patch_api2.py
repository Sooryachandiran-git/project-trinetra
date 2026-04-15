import os
filepath = r"e:\Projects\project-trinetra\backend-orchestrator\api\control.py"
with open(filepath, "a") as f:
    f.write("\n\n@router.post('/attacks/atk13/enable')\nasync def enable_atk13_demo():\n    from main import sim_engine\n    sim_engine.set_attack_state('atk13_gps_desync', True)\n    return {'status': 'success'}\n")
print("api patched")
