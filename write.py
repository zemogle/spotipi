import RPi.GPIO as GPIO
import logging

from mfrc522 import SimpleMFRC522

reader = SimpleMFRC522()

if __name__ == '__main__':
    try:
            text = input('New data:')
            print("Now place your tag to write")
            reader.write(text)
            print("Written")
    finally:
            GPIO.cleanup()
