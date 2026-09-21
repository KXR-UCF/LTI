import { SwitchState } from '../types/telemetry';

export class SwitchStateManager {
  private state: SwitchState;

  constructor() {
    // Initialize all to False (Close/Disable)
    this.state = {
      switch1: false,
      switch2: false,
      switch3: false,
      switch4: false,
      switch5: false,
      switch6: false,
      switch7: false,
      switch8: false,
      switch9: false,
      switch10: false,
      continuity: false, // Defaulting to false as it's not in the pipe logic yet
      launchKey: false,
      abort: false,
    };
  }

  /**
   * Returns a copy of the current state to prevent external mutation
   */
  public getState(): SwitchState {
    return { ...this.state };
  }

  /**
   * Parses string messages from Python pipe and updates boolean state
   * Logic matches socket_client.py format
   */
  public parseAndUpdate(rawMessage: string): void {
    const msg = rawMessage.trim();
    if (!msg) return;

    // 1. Handle Numbered Switches ("1 Open", "5 Close")
    const switchMatch = msg.match(/^(\d+)\s+(Open|Close)$/);
    if (switchMatch) {
      const id = switchMatch[1];
      const statusStr = switchMatch[2]; // "Open" or "Close"
      const key = `switch${id}`;
      
      // Map "Open" -> true, "Close" -> false
      const isOpen = statusStr === 'Open';

      // Only update if this switch key actually exists in our state
      if (this.state.hasOwnProperty(key)) {
        this.state[key] = isOpen;
      }
      return;
    }

    // 2. Handle Launch Key ("ENABLE FIRE", "DISABLE FIRE")
    if (msg === 'ENABLE FIRE') {
      this.state.launchKey = true;
      return;
    }
    if (msg === 'DISABLE FIRE') {
      this.state.launchKey = false;
      return;
    }

    // 3. Handle Abort ("ABORT Open", "ABORT Close")
    // Based on Python script: "ABORT Open" maps to state=True
    if (msg === 'ABORT Open') {
      this.state.abort = true;
      return;
    }
    if (msg === 'ABORT Close') {
      this.state.abort = false;
      return;
    }
  }
}