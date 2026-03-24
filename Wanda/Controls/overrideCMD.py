import time
import threading

class OverrideManager:
    
    def __init__(self, controller_instance):
        self.controller = controller_instance
        # self.fire_enabled = False
        self.active_thread = None

    def process_command(self, switch_id, state):
        cmd = str(switch_id).lower()
        if cmd in self.OVERRIDDEN_CMDS:
            if self.active_thread and self.active_thread.is_alive():
                return True
            self.active_thread = threading.Thread(target=self.OVERRIDDEN_CMDS[cmd], args=(self, state))
            self.active_thread.start()
            return True
        return False   

    # TEST SEQUENCE
    def run_fire(self, state):
        if state:  # Only execute sequence if FIRE is set to True
            for pi_id in ["controller", "1"]:
                for relay_id in range(1, 9):
                    self.controller.set_relay(pi_id, relay_id, True)
                    time.sleep(0.5)

    def run_fire_key(self, state):
        if state:
            pass # Add logic for ENABLE FIRE here
        else:
            pass # Add logic for DISABLE FIRE here

    OVERRIDDEN_CMDS = {
        "fire": run_fire,
        "fire key": run_fire_key,
    }
