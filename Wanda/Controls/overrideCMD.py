import time
import threading

class OverrideManager:
    
    def __init__(self, controller_instance):
        self.controller = controller_instance
        # self.fire_enabled = False
        self.active_thread = None

    def process_command(self, cmd_name):
        cmd = cmd_name.lower()
        if cmd in self.OVERRIDDEN_CMDS:
            if self.active_thread and self.active_thread.is_alive():
                return True
            self.active_thread = self.OVERRIDDEN_CMDS[cmd](self.controller)
            return True
        return False   

    # TEST SEQUENCE
    def run_fire(self):
        for pi_id in ["controller", "1"]:
            for relay_id in range(1, 9):
                self.controller.set_relay(pi_id, relay_id, True)
                time.sleep(0.5)


    def run_enable_fire(self):
        pass

    def run_disable_fire(self):
        pass

    OVERRIDDEN_CMDS = {
        "fire": run_fire,
        "enable fire": run_enable_fire,
        "disable fire": run_disable_fire,
    }
