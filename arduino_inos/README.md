## Arduino Files
These two files allow data to be entered into the database, and therefore displayed on the graph page

To keep wifi credentials off Git, there is a script used to write your wifi credentials to the EEPROM of the ESP32
Then when post_voltage_esp32 script is loaded, it can read the values off of the ROM on setup.
