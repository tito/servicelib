print "hello from service 2"
import time
for x in range(10):
    time.sleep(.5)
    print "service 2:", x
print "bye bye from service 2"
