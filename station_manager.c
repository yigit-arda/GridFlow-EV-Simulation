#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "gridflow_core.h"

/* Physical power ceiling of a socket by connector type. Single place that
 * defines it, so ETA estimates and actual delivered energy can't disagree. */
static float socketPowerLimit(ChargeType type) {
    return (type == AC_TYPE2) ? 22.0f : 120.0f;
}

/* The power a vehicle would draw on a given socket if it had the grid all
 * to itself: the smaller of what the car can accept and what the socket
 * can physically deliver. This is the *desired* power, before fair-share
 * throttling against maxGridCap. */
static float effectivePower(ChargingSocket *socket, EVehicle *car) {
    float limit = socketPowerLimit(socket->charge_type);
    return (car->maxChgPwr > limit) ? limit : car->maxChgPwr;
}

/* --- Dynamic load balancing ---
 * Recomputes, for every socket, how much power it should actually be
 * drawing right now, and writes the result into ChargingSocket.currPwr
 * (and the station-wide total). This is the single source of truth used
 * everywhere else (getActivePower, getTotalPower, the grid-load bar):
 *   - A socket whose vehicle already reached its target wants 0 kW.
 *   - Otherwise a socket wants effectivePower() kW.
 *   - If the sum of everyone's wants exceeds maxGridCap, every active
 *     socket is scaled down proportionally (fair share) instead of any
 *     vehicle being denied a connection.
 * Called right after plug/unplug (so the UI reflects the new distribution
 * immediately) and at the start of every advanceTime tick. */
static void recomputeGridDistribution(Station *station) {
    if (station == NULL || station->totalSocketNo <= 0) return;

    int n = station->totalSocketNo;
    /* Heap-allocated rather than a VLA: keeps this portable to compilers
     * (e.g. MSVC) that don't support variable-length arrays. */
    float *desired = malloc(sizeof(float) * n);
    if (desired == NULL) return;
    float totalDesired = 0.0f;

    for (int i = 0; i < n; i++) {
        if (station->sockets[i].isFull) {
            EVehicle *car = station->sockets[i].connectedVehicle;
            if (car->currBatLvl < car->tgtBatLvl) {
                desired[i] = effectivePower(&station->sockets[i], car);
                totalDesired += desired[i];
            } else {
                desired[i] = 0.0f; /* target reached - draws nothing */
            }
        } else {
            desired[i] = 0.0f;
        }
    }

    float scale = 1.0f;
    if (totalDesired > station->maxGridCap && totalDesired > 0.0f) {
        scale = station->maxGridCap / totalDesired;
    }

    float sumActual = 0.0f;
    for (int i = 0; i < n; i++) {
        float actual = desired[i] * scale;
        station->sockets[i].currPwr = actual;
        sumActual += actual;
    }
    station->totCurrPwr = sumActual;
    free(desired);
}


Station *initStation(float maxCapacity, int totalSocketNo) {

    Station *newStation = malloc(sizeof(Station));

    if (newStation == NULL) {
        printf("Error: The place for station could not be reserved!\n");
        return NULL;
    }

    newStation->maxGridCap = maxCapacity;
    newStation->totalSocketNo = totalSocketNo;

    newStation->totCurrPwr = 0.0;

    newStation->sockets = malloc(sizeof(ChargingSocket) * totalSocketNo);

    for (int i = 0; i < totalSocketNo; i++) {
        newStation->sockets[i].socketID = i + 1;

        newStation->sockets[i].isFull = false;

        newStation->sockets[i].currPwr = 0.0;

        newStation->sockets[i].connectedVehicle = NULL;


        if (i < totalSocketNo / 2) {
            newStation->sockets[i].charge_type = AC_TYPE2;
        } else {
            newStation->sockets[i].charge_type = DC_CCS;
        }
    }

    newStation->waitList = malloc(sizeof(WaitQueue));

    if (newStation->waitList == NULL) {
        printf("Error: The place for wait list could not be reserved!");
        return NULL;
    }

    newStation->waitList->head = NULL;

    newStation->waitList->currentSize = 0;


    newStation->currentTime = 0;
    newStation->idleGracePeriod = 15;
    newStation->feePerMinute = 5.0;

    newStation->pricePerKwhAC = 9.5;
    newStation->pricePerKwhDC = 12.5;

    newStation->lifetimeChargeRevenue = 0.0f;
    newStation->lifetimePenaltyRevenue = 0.0f;
    newStation->lifetimeSessionCount = 0;


    time_t t = time(NULL);
    struct tm *tm = localtime(&t);
    newStation->baseStartMinute = (tm->tm_hour * 60) + tm->tm_min;



    return newStation;
}

EVehicle *createVehicle(const char *plate, ChargeType type, float currSoc, float tgtSoc, float maxPwr, int prio) {

    EVehicle *newCar = malloc(sizeof(EVehicle));

    if (newCar == NULL) {
        printf("Error: The place for new car could not be reserved!\n");
        return NULL;
    }

    /* Bounded copy: an oversized plate string used to overflow license_plate[16]. */
    strncpy(newCar->license_plate, plate, sizeof(newCar->license_plate) - 1);
    newCar->license_plate[sizeof(newCar->license_plate) - 1] = '\0';

    newCar->charge_type = type;

    newCar->currBatLvl = currSoc;

    newCar->tgtBatLvl = tgtSoc;

    newCar->maxChgPwr = maxPwr;

    newCar->chgPrio = prio;


    newCar->plugInTime = 0;
    newCar->expectedFinishTime = 0;
    newCar->idleFee = 0.0;

    newCar->totalChargeCost = 0.0;


    return newCar;
}

void freeVehicle(EVehicle *car) {
    if (car != NULL) {
        free(car);
    }
}

void freeStation(Station *station) {

    if (station != NULL) {

        if (station->sockets != NULL) {
            for (int i = 0; i < station->totalSocketNo; i++) {
                if (station->sockets[i].connectedVehicle != NULL) {
                    freeVehicle(station->sockets[i].connectedVehicle);
                    station->sockets[i].connectedVehicle = NULL;
                }
            }
            free(station->sockets);
        }

        if (station->waitList != NULL) {

            QueueNode *current = station->waitList->head;
            QueueNode *temp;

            while (current != NULL) {

                temp = current;
                current = current->next;
                freeVehicle(temp->car);
                free(temp);
            }

            free(station->waitList);
        }

        free(station);
    }

}

bool enqueueVehicle(WaitQueue *queue, EVehicle *car) {

    if (queue == NULL || car == NULL) {
        return false;
    }


    QueueNode *newNode = malloc(sizeof(QueueNode));

    if (newNode == NULL) {

        printf("Error: New node could not be created!");
        return false;
    }


    newNode->car = car;

    newNode->next = NULL;


    if (queue->head == NULL || car->chgPrio < queue->head->car->chgPrio) {

        newNode->next = queue->head;

        queue->head = newNode;
    } else {
        QueueNode *current = queue->head;

        while (current->next != NULL && current->next->car->chgPrio <= car->chgPrio) {
            current = current->next;
        }

        newNode->next = current->next;
        current->next = newNode;

    }

    queue->currentSize++;


    return true;

}




void displayQueue(Station *station) {

    if (station == NULL || station->waitList == NULL) {
        printf("Error: Station or WaitList is not initialized!\n");
        return;
    }

    printf("Number of vehicles waiting in the queue: %d\n", station->waitList->currentSize);
    printf("--------------------------------------------------\n");

    QueueNode *current = station->waitList->head;
    int index = 1;

    while (current != NULL) {
        printf("%d. Vehicle in queue: %-15s | Priority: %d\n",
               index, current->car->license_plate, current->car->chgPrio);
        current = current->next;
        index++;
    }
    printf("--------------------------------------------------\n");
}


int plugVehicle(Station *station, EVehicle *car) {

    if (station == NULL || car == NULL) {
        return -1;
    }

    for (int i = 0; i < station->totalSocketNo; i++) {

        if (station->sockets[i].isFull == false && station->sockets[i].charge_type == car->charge_type) {

            station->sockets[i].connectedVehicle = car;
            station->sockets[i].isFull = true;

            car->plugInTime = station->currentTime;

            /* Best-case ETA assuming this car gets its full desired power
             * with no grid contention. Dynamic load balancing may slow
             * this down in practice if the grid gets busy - shown to the
             * user as an estimate, same as a real charging network would. */
            float candidatePower = effectivePower(&station->sockets[i], car);
            float energyNeeded = (car->tgtBatLvl) - (car->currBatLvl);
            int requiredMinutes = (int)((energyNeeded / candidatePower) * 60.0);

            car->expectedFinishTime = station->currentTime + requiredMinutes;

            int plugRealTotal = station->baseStartMinute + car->plugInTime;
            int plugHour = (plugRealTotal / 60) % 24;
            int plugMin = plugRealTotal % 60;

            int finishRealTotal = station->baseStartMinute + car->expectedFinishTime;
            int finishHour = (finishRealTotal / 60) % 24;
            int finishMin = finishRealTotal % 60;

            printf("Vehicle %s is successfully plugged into socket %d.\n", car->license_plate, station->sockets[i].socketID);
            printf("   [Plugged in at: %02d:%02d | Expected Finish: %02d:%02d | Duration: %d mins]\n",
                   plugHour, plugMin, finishHour, finishMin, requiredMinutes);

            /* Refresh the fair-share power distribution immediately so the
             * UI doesn't have to wait for the next advanceTime tick to
             * reflect this new vehicle joining the grid. */
            recomputeGridDistribution(station);

            return station->sockets[i].socketID;
        }
    }

    printf("No available socket found. Vehicle %s is being added to the queue...\n", car->license_plate);
    return enqueueVehicle(station->waitList, car) ? 0 : -1;
}

EVehicle *dequeueVehicle(WaitQueue *queue) {

    if (queue == NULL || queue->head == NULL) {
        return NULL;
    }

    QueueNode *temp = queue->head;

    EVehicle *currentVehicle = temp->car;

    queue->head = queue->head->next;

    free(temp);

    queue->currentSize--;

    return currentVehicle;

}


void unplugVehicle(Station *station, int socketID) {


    if (socketID < 1 || socketID > station->totalSocketNo) {
        printf("Error: Invalid socket!\n");
        return;
    }

    int realID = socketID - 1;

    if (station->sockets[realID].isFull == false) {
        printf("This socket is already empty.\n");
        return;
    } else {
        EVehicle *leaving = station->sockets[realID].connectedVehicle;

        /* Fold this vehicle's bill into the station's permanent lifetime
         * totals before it is freed, so a stats screen can show revenue
         * even long after this car has driven off. */
        station->lifetimeChargeRevenue += leaving->totalChargeCost;
        station->lifetimePenaltyRevenue += leaving->idleFee;
        station->lifetimeSessionCount += 1;

        freeVehicle(leaving);
        station->sockets[realID].connectedVehicle = NULL;
        station->sockets[realID].currPwr = 0.0;
        station->sockets[realID].isFull = false;

        printf("Vehicle at socket %d has disconnected. The socket is now EMPTY.\n", socketID);
    }


    EVehicle *nextCar = dequeueVehicle(station->waitList);

    if (nextCar != NULL) {
        printf(">> Autopilot: Next vehicle in the queue is being directed to the socket...\n");
        plugVehicle(station, nextCar); /* also re-runs recomputeGridDistribution */
    } else {
        recomputeGridDistribution(station);
    }

}


void advanceTime(Station *station, int minutes) {

    station->currentTime += minutes;
    int currentRealTotal = station->baseStartMinute + station->currentTime;
    int currHour = (currentRealTotal / 60) % 24;
    int currMin = currentRealTotal % 60;

    printf("--- TIME ADVANCED: +%d mins [CURRENT CLOCK: %02d:%02d] ---\n",
           minutes, currHour, currMin);

    /* Fair-share the grid across everyone who still needs energy - this is
     * what makes sockets.currPwr trustworthy for the rest of this tick. */
    recomputeGridDistribution(station);

    for (int i = 0; i < station->totalSocketNo; i++) {

        if (station->sockets[i].isFull == true) {
            EVehicle *car = station->sockets[i].connectedVehicle;


            if (car->currBatLvl < car->tgtBatLvl) {

                float activePwr = station->sockets[i].currPwr; /* fair-share distributed */

                float fetchedEnergy = activePwr * (minutes / 60.0);

                if (station->sockets[i].charge_type == AC_TYPE2) {
                    car->totalChargeCost += fetchedEnergy * station->pricePerKwhAC;
                } else {
                    car->totalChargeCost += fetchedEnergy * station->pricePerKwhDC;
                }

                car->currBatLvl += fetchedEnergy;


                if (car->currBatLvl >= car->tgtBatLvl) {
                    car->currBatLvl = car->tgtBatLvl;
                    car->expectedFinishTime = station->currentTime;
                    /* From here on this socket wants 0 kW - the *next*
                     * recomputeGridDistribution call (next tick, or the
                     * next plug/unplug) will reflect that. */
                }
            }

            else {
                /* Target already reached: draws no power, only risks the
                 * idle fee once the grace period is exceeded. */
                int delayTime = station->currentTime - car->expectedFinishTime;

                if (delayTime > station->idleGracePeriod) {
                    int penaltyDuration = delayTime - station->idleGracePeriod;
                    car->idleFee = penaltyDuration * station->feePerMinute;

                    printf("WARNING: Vehicle [%s] has been overstaying for %d minutes. Current Fee: $%.2f \n",
                           car->license_plate, penaltyDuration, car->idleFee);
                }
            }

        }
    }
}

/* ---------------- Getters ---------------- */

static bool validSocket(Station *station, int socketID) {
    return station != NULL && socketID > 0 && socketID <= station->totalSocketNo;
}

bool isSocketFull(Station *station, int socketID) {
    if (!validSocket(station, socketID)) return false;
    return station->sockets[socketID - 1].isFull;
}

ChargeType getSocketChargeType(Station *station, int socketID) {
    if (!validSocket(station, socketID)) return AC_TYPE2;
    return station->sockets[socketID - 1].charge_type;
}

const char *getPlateAt(Station *station, int socketID) {
    if (!validSocket(station, socketID) || !station->sockets[socketID - 1].isFull) return NULL;
    return station->sockets[socketID - 1].connectedVehicle->license_plate;
}

float getSocketSOC(Station *station, int socketID) {
    int realID = socketID - 1;
    if (validSocket(station, socketID) && station->sockets[realID].isFull) {
        return station->sockets[realID].connectedVehicle->currBatLvl;
    }
    return 0.0;
}

float getTargetSOC(Station *station, int socketID) {
    int realID = socketID - 1;
    if (validSocket(station, socketID) && station->sockets[realID].isFull) {
        return station->sockets[realID].connectedVehicle->tgtBatLvl;
    }
    return 0.0;
}

float getChargeCost(Station *station, int socketID) {
    int realID = socketID - 1;
    if (validSocket(station, socketID) && station->sockets[realID].isFull) {
        return station->sockets[realID].connectedVehicle->totalChargeCost;
    }
    return 0.0;
}

float getIdleFee(Station *station, int socketID) {
    int realID = socketID - 1;
    if (validSocket(station, socketID) && station->sockets[realID].isFull) {
        return station->sockets[realID].connectedVehicle->idleFee;
    }
    return 0.0;
}

int getExpectedFinishReal(Station *station, int socketID) {
    int realID = socketID - 1;
    if (validSocket(station, socketID) && station->sockets[realID].isFull) {
        return station->baseStartMinute + station->sockets[realID].connectedVehicle->expectedFinishTime;
    }
    return -1;
}

/* Ground truth: whatever the last recomputeGridDistribution() decided this
 * socket should be drawing right now (already 0 once a vehicle is done). */
float getActivePower(Station *station, int socketID) {
    int realID = socketID - 1;
    if (validSocket(station, socketID) && station->sockets[realID].isFull) {
        return station->sockets[realID].currPwr;
    }
    return 0.0;
}

int getQueueSize(Station *station) {
    if (station == NULL || station->waitList == NULL) return 0;
    return station->waitList->currentSize;
}

const char *getQueuePlateAt(Station *station, int index) {
    if (station == NULL || station->waitList == NULL || index < 0) return NULL;

    QueueNode *current = station->waitList->head;
    int i = 0;
    while (current != NULL) {
        if (i == index) return current->car->license_plate;
        current = current->next;
        i++;
    }
    return NULL;
}

int getQueueEstimatedWaitMinutes(Station *station, int index) {
    if (station == NULL || station->waitList == NULL || index < 0) return -1;

    QueueNode *target = station->waitList->head;
    int i = 0;
    while (target != NULL && i < index) { target = target->next; i++; }
    if (target == NULL) return -1;

    ChargeType type = target->car->charge_type;
    int n = station->totalSocketNo;
    int *finishTimes = malloc(sizeof(int) * n);
    if (finishTimes == NULL) return -1;
    int count = 0;

    for (int s = 0; s < n; s++) {
        if (station->sockets[s].isFull && station->sockets[s].charge_type == type) {
            EVehicle *c = station->sockets[s].connectedVehicle;
            /* If already finished but nobody has unplugged it yet, we
             * optimistically assume "any minute now" for this estimate. */
            int f = (c->currBatLvl < c->tgtBatLvl) ? c->expectedFinishTime : station->currentTime;
            finishTimes[count++] = f;
        }
    }

    if (count == 0) { free(finishTimes); return -1; } /* no socket of that type exists */

    /* simple insertion sort - count is tiny (== number of sockets) */
    for (int a = 1; a < count; a++) {
        int key = finishTimes[a];
        int b = a - 1;
        while (b >= 0 && finishTimes[b] > key) {
            finishTimes[b + 1] = finishTimes[b];
            b--;
        }
        finishTimes[b + 1] = key;
    }

    /* how many same-type vehicles are queued strictly ahead of this one */
    int aheadCount = 0;
    QueueNode *cur = station->waitList->head;
    while (cur != target) {
        if (cur->car->charge_type == type) aheadCount++;
        cur = cur->next;
    }

    int slot = (aheadCount >= count) ? count - 1 : aheadCount;
    int waitMinutes = finishTimes[slot] - station->currentTime;
    free(finishTimes);
    return (waitMinutes < 0) ? 0 : waitMinutes;
}

float getTotalPower(Station *station) {
    if (station == NULL) return 0.0;
    return station->totCurrPwr;
}

float getMaxCapacity(Station *station) {
    if (station == NULL) return 0.0;
    return station->maxGridCap;
}

int getStationClock(Station *station) {
    if (station == NULL) return 0;
    return station->baseStartMinute + station->currentTime;
}

int getElapsedMinutes(Station *station) {
    if (station == NULL) return 0;
    return station->currentTime;
}

float getLifetimeChargeRevenue(Station *station) {
    if (station == NULL) return 0.0;
    return station->lifetimeChargeRevenue;
}

float getLifetimePenaltyRevenue(Station *station) {
    if (station == NULL) return 0.0;
    return station->lifetimePenaltyRevenue;
}

int getLifetimeSessionCount(Station *station) {
    if (station == NULL) return 0;
    return station->lifetimeSessionCount;
}
