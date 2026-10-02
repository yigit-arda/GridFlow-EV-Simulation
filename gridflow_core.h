/* gridflow_core.h */

#ifndef GRIDFLOW_CORE_H
#define GRIDFLOW_CORE_H

#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

/* Defines the physical connector types supported by the station. */
typedef enum {

    AC_TYPE2,
    DC_CCS

} ChargeType;

/* Represents an individual electric vehicle along with its charging requirements and session billing data. */
typedef struct {

    char license_plate[16]; /* Vehicle identification string */

    ChargeType charge_type; /* Hardware compatibility of the vehicle */

    float currBatLvl;       /* Current State of Charge (SOC) */
    float tgtBatLvl;        /* Target State of Charge requested by the driver */
    float maxChgPwr;        /* Maximum power the vehicle's onboard charger can handle */
    int chgPrio;            /* Priority level for queue ordering (lower number = higher priority) */

    int plugInTime;         /* The simulated minute when the vehicle was plugged in */
    int expectedFinishTime; /* The simulated minute when charging is estimated to complete */
    float idleFee;          /* Accumulated penalty fee for overstaying */

    float totalChargeCost;  /* Accumulated cost for the consumed energy */

} EVehicle;

/* Represents a single physical charging bay in the station. */
typedef struct {

    int socketID;           /* Unique identifier for the socket (1-indexed) */

    ChargeType charge_type; /* Hardware connector type of this socket */

    bool isFull;            /* Indicates if a vehicle is currently connected */
    float currPwr;          /* Actual active power currently flowing through this socket */

    EVehicle *connectedVehicle; /* Pointer to the connected vehicle, NULL if empty */

} ChargingSocket;

/* A single node in the waiting queue linked list. */
typedef struct QueueNode {

    EVehicle *car;          /* Pointer to the queued vehicle */

    struct QueueNode *next; /* Pointer to the next node in the queue */

} QueueNode;

/* Manages the priority linked list of vehicles waiting for an available socket. */
typedef struct {

    QueueNode *head;        /* First vehicle in the line */
    int currentSize;        /* Total number of vehicles currently waiting */

} WaitQueue;

/* The main simulation state object containing all sockets, queues, and global station parameters. */
typedef struct {

    float maxGridCap;       /* Maximum total power the station's transformer can deliver */
    float totCurrPwr;       /* Current active power being drawn by all sockets combined */
    int totalSocketNo;      /* Total number of physical sockets in the station */

    ChargingSocket *sockets;/* Dynamic array of all sockets */
    WaitQueue *waitList;    /* Pointer to the station's waiting queue */

    int currentTime;        /* Simulated elapsed time in minutes */
    int baseStartMinute;    /* Real-world start time locked at initialization (in minutes from midnight) */
    int idleGracePeriod;    /* Allowed free minutes after charging completes before penalties apply */
    float feePerMinute;     /* Penalty cost per minute for overstaying */

    float pricePerKwhAC;    /* Billing rate for AC charging */
    float pricePerKwhDC;    /* Billing rate for DC charging */

    /* Persistent (session-lifetime) statistics. These survive individual
     * plug/unplug cycles - once a vehicle settles its bill at unplug time,
     * its contribution is folded in here permanently, so a stats screen can
     * show station totals even after every car has driven off. */
    float lifetimeChargeRevenue;
    float lifetimePenaltyRevenue;
    int lifetimeSessionCount;

} Station;


/* --- Lifecycle --- */

/* Allocates memory and initializes the station, its sockets, and default pricing values. */
Station *initStation(float maxCapacity, int totalSocketNo);

/* Allocates memory for a new vehicle and safely populates its parameters. */
EVehicle *createVehicle(const char *plate, ChargeType type, float currSoc, float tgtSoc, float maxPwr, int prio);

/* Safely frees the memory allocated for a specific vehicle. */
void freeVehicle(EVehicle *car);

/* Safely tears down the entire station, freeing all connected vehicles, queued vehicles, and arrays to prevent memory leaks. */
void freeStation(Station *station);

/* --- Core operations ---
 * plugVehicle returns:
 *   > 0  -> the socketID the vehicle was actually plugged into
 *     0  -> no free/eligible socket right now, vehicle was added to the wait queue
 *    -1  -> invalid call (NULL station/car)
 * Admission is no longer blocked by grid capacity - instead, every tick the
 * available capacity is fair-shared across all actively charging sockets
 * (see the dynamic load balancing note on advanceTime).
 */
int plugVehicle(Station *station, EVehicle *car);

/* Inserts a vehicle into the wait queue based on its priority level. */
bool enqueueVehicle(WaitQueue *queue, EVehicle *car);

/* Removes and returns the highest priority vehicle from the front of the queue. */
EVehicle *dequeueVehicle(WaitQueue *queue);

/* Disconnects a vehicle, settles its lifetime bill, and automatically triggers the autopilot to pull the next waiting vehicle. */
void unplugVehicle(Station *station, int socketID);

/* Prints the current state of the wait queue to the console for debugging purposes. */
void displayQueue(Station *station);

/* Advances the simulation clock. Every call first re-distributes the
 * station's maxGridCap fairly across all sockets that still need energy
 * (dynamic load balancing): if the sum of what everyone wants exceeds the
 * grid cap, every active session is throttled proportionally instead of
 * any vehicle being refused a socket outright. A socket whose vehicle has
 * already reached its target draws 0 kW from that point on - it only ever
 * costs it the idle fee once the grace period is exceeded. */
void advanceTime(Station *station, int minutes);

/* --- Per-socket getters (read-only, safe with invalid IDs) --- */

/* Checks if a specific socket is currently occupied. */
bool isSocketFull(Station *station, int socketID);

/* Retrieves the hardware charge type of a specific socket. */
ChargeType getSocketChargeType(Station *station, int socketID);

/* Retrieves the license plate of the vehicle currently connected to a specific socket. */
const char *getPlateAt(Station *station, int socketID);

/* Retrieves the current State of Charge of the vehicle at a specific socket. */
float getSocketSOC(Station *station, int socketID);

/* Retrieves the target State of Charge requested by the vehicle at a specific socket. */
float getTargetSOC(Station *station, int socketID);

/* Retrieves the actual active power currently being drawn from a specific socket. */
float getActivePower(Station *station, int socketID);

/* Retrieves the accumulated charging cost for the vehicle at a specific socket. */
float getChargeCost(Station *station, int socketID);

/* Retrieves the accumulated penalty fee for the vehicle at a specific socket. */
float getIdleFee(Station *station, int socketID);

/* Retrieves the real-world estimated completion time (in minutes from midnight) for a specific socket. */
int getExpectedFinishReal(Station *station, int socketID);

/* --- Wait queue getters --- */

/* Retrieves the total number of vehicles currently in the queue. */
int getQueueSize(Station *station);

/* Retrieves the license plate of a queued vehicle at a specific index. */
const char *getQueuePlateAt(Station *station, int index);

/* Rough estimate (minutes) of how long a queued vehicle should still wait,
 * based on when same-type sockets are next expected to free up. Returns -1
 * if it cannot be estimated (e.g. no socket of that type exists at all). */
int getQueueEstimatedWaitMinutes(Station *station, int index);



/* --- Station-level getters --- */

/* Retrieves the total active power currently being drawn across the entire station. */
float getTotalPower(Station *station);

/* Retrieves the absolute maximum hardware power capacity of the station's grid. */
float getMaxCapacity(Station *station);

/* Retrieves the current simulated clock time (in minutes from midnight). */
int getStationClock(Station *station);

/* Retrieves the requested charge type of a queued vehicle at a specific index. */
int getQueueChargeTypeAt(Station *station, int index);


/* Monotonic simulated minutes elapsed since the station started (unlike
 * getStationClock, this never wraps at midnight) - handy as a chart x-axis. */
int getElapsedMinutes(Station *station);



/* --- Lifetime / persistent statistics getters --- */

/* Retrieves the total charging revenue collected since the station was initialized. */
float getLifetimeChargeRevenue(Station *station);

/* Retrieves the total penalty revenue collected since the station was initialized. */
float getLifetimePenaltyRevenue(Station *station);

/* Retrieves the total number of completed charging sessions. */
int getLifetimeSessionCount(Station *station);

#endif