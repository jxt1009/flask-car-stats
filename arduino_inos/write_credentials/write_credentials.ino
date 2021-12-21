#include "EEPROM.h"

// Modified version of simple script to write to EEPROM
// Mainly for keeping sensitive info off git, values can
// be read from rom instead of hard coding them in plain text

int addr = 0;
#define EEPROM_SIZE 64

// the sample text which we are storing in EEPROM
char ssid[64] = "BillClinternet|Reggie08";

void setup() {
    Serial.begin(115200);
    Serial.println("Writing now...");

    if (!EEPROM.begin(EEPROM_SIZE)) {
        Serial.println("Failed to access EEPROM");
        delay(1000000);
    }else{
      write_to_eeprom(ssid);
    }
}
void write_to_eeprom(char val[]){
    // writing byte-by-byte to EEPROM
    for (int i = 0; i < EEPROM_SIZE; i++) {
        EEPROM.write(addr, ssid[i]);
        addr += 1;
    }
    String check_str = check_eeprom();
    if(check_str != ""){
      EEPROM.commit();
      Serial.print("SUCCESS. WROTE TO EEPROM: ");
      Serial.println(check_str);
    }
}

String check_eeprom(){
    String return_val = "";
    // reading byte-by-byte from EEPROM
    for (int i = 0; i < EEPROM_SIZE; i++) {
        byte readValue = EEPROM.read(i);

        if (readValue == 0) {
            break;
        }

        char readValueChar = char(readValue);
        return_val+=readValueChar;
    }
    return return_val;
}

void loop() {

}
