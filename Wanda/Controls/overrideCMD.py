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
        self.controller.set_relay("wanda1", 6, True)
        self.controller.set_relay("wanda1", 7, True)

        fire_start = time.perf_counter()

        while (time.perf_counter() - fire_start) * 1000 < 100:
            time.sleep(0.001)
        self.controller.set_relay("wanda2", 1, True)
        
        while (time.perf_counter() - fire_start) * 1000 < 200:
            time.sleep(0.001)
        self.controller.set_relay("wanda2", 2, True)

        while (time.perf_counter() - fire_start) * 1000 < 300:
            time.sleep(0.001)
        self.controller.set_relay("wanda1", 8, True)
        

        




    def run_fire_key(self, state):
        if state:
            self.controller.set_relay("wanda1", 6, True);
            self.controller.set_relay("wanda1", 7, True);
        else:
            self.controller.set_relay("wanda1", 6, False);
            self.controller.set_relay("wanda1", 7, False);
            self.controller.set_relay("wanda2", 1, False);
            self.controller.set_relay("wanda2", 2, False);
            self.controller.set_relay("wanda1", 8, False);

    OVERRIDDEN_CMDS = {
        "fire": run_fire,
        "fire key": run_fire_key,
    }
