#ifndef GRIDFLOW_CORE_H
#define GRIDFLOW_CORE_H

#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

typedef enum {

    AC_TYPE2,
    DC_CCS

} ChargeType;

typedef struct {

    char license_plate[16];

    ChargeType charge_type;

    float currBatLvl;
    float tgtBatLvl;
    float maxChgPwr;
    int chgPrio;

    int plugInTime;
    int expectedFinishTime;
    float idleFee;

    float totalChargeCost;

} EVehicle;

typedef struct {

    int socketID;

    ChargeType charge_type;

    bool isFull;
    float currPwr;

    EVehicle *connectedVehicle;

} ChargingSocket;


typedef struct QueueNode {

    EVehicle *car;

    struct QueueNode *next;

} QueueNode;

typedef struct {

    QueueNode *head;
    int currentSize;

} WaitQueue;

typedef struct {

    float maxGridCap;
    float totCurrPwr;
    int totalSocketNo;

    ChargingSocket *sockets;
    WaitQueue *waitList;

    int currentTime;
    int baseStartMinute;
    int idleGracePeriod;
    float feePerMinute;

    float pricePerKwhAC;
    float pricePerKwhDC;

    /* Persistent (session-lifetime) statistics. These survive individual
     * plug/unplug cycles - once a vehicle settles its bill at unplug time,
     * its contribution is folded in here permanently, so a stats screen can
     * show station totals even after every car has driven off. */
    float lifetimeChargeRevenue;
    float lifetimePenaltyRevenue;
    int lifetimeSessionCount;

} Station;


/* --- Lifecycle --- */
Station *initStation(float maxCapacity, int totalSocketNo);
EVehicle *createVehicle(const char *plate, ChargeType type, float currSoc, float tgtSoc, float maxPwr, int prio);
void freeVehicle(EVehicle *car);
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
bool enqueueVehicle(WaitQueue *queue, EVehicle *car);
EVehicle *dequeueVehicle(WaitQueue *queue);
void unplugVehicle(Station *station, int socketID);
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
bool isSocketFull(Station *station, int socketID);
ChargeType getSocketChargeType(Station *station, int socketID);
const char *getPlateAt(Station *station, int socketID);
float getSocketSOC(Station *station, int socketID);
float getTargetSOC(Station *station, int socketID);
float getActivePower(Station *station, int socketID);
float getChargeCost(Station *station, int socketID);
float getIdleFee(Station *station, int socketID);
int getExpectedFinishReal(Station *station, int socketID);

/* --- Wait queue getters --- */
int getQueueSize(Station *station);
const char *getQueuePlateAt(Station *station, int index);
/* Rough estimate (minutes) of how long a queued vehicle should still wait,
 * based on when same-type sockets are next expected to free up. Returns -1
 * if it cannot be estimated (e.g. no socket of that type exists at all). */
int getQueueEstimatedWaitMinutes(Station *station, int index);



/* --- Station-level getters --- */
float getTotalPower(Station *station);
float getMaxCapacity(Station *station);
int getStationClock(Station *station);
int getQueueChargeTypeAt(Station *station, int index);


/* Monotonic simulated minutes elapsed since the station started (unlike
 * getStationClock, this never wraps at midnight) - handy as a chart x-axis. */
int getElapsedMinutes(Station *station);



/* --- Lifetime / persistent statistics getters --- */
float getLifetimeChargeRevenue(Station *station);
float getLifetimePenaltyRevenue(Station *station);
int getLifetimeSessionCount(Station *station);

#endif