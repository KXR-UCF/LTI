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
        self.controller.set_relay("controller", 1, True)
        time.sleep(0.5)
        self.controller.set_relay("controller", 2, True)
        time.sleep(0.5)
        self.controller.set_relay("controller", 3, True)
        time.sleep(0.5)
        self.controller.set_relay("controller", 4, True)
        time.sleep(0.5)
        self.controller.set_relay("controller", 5, True)
        time.sleep(0.5)
        self.controller.set_relay("controller", 6, True)
        time.sleep(0.5)
        self.controller.set_relay("controller", 7, True)
        time.sleep(0.5)
        self.controller.set_relay("controller", 8, True)
        time.sleep(0.5)
        self.controller.set_relay("1", 1, True)
        time.sleep(0.5)
        self.controller.set_relay("1", 2, True)
        time.sleep(0.5)
        self.controller.set_relay("1", 3, True)
        time.sleep(0.5)
        self.controller.set_relay("1", 4, True)
        time.sleep(0.5)
        self.controller.set_relay("1", 5, True)
        time.sleep(0.5)
        self.controller.set_relay("1", 6, True)
        time.sleep(0.5)
        self.controller.set_relay("1", 7, True)
        time.sleep(0.5)
        self.controller.set_relay("1", 8, True)
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
