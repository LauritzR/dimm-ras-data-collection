#!/usr/bin/python3
import sys, os,csv
import json

def print_csv(li):
    print(";".join(li[0]))
    for line in li:
        lista = []
        for item in line:
            lista.append(str(line[item]))
        print(";".join(lista))

def syslog_analysis():
    syslog_list = []
    for filename in sys.argv[1:]:
        if not os.path.isfile(filename):
            print(f"File {filename} desn't exist")
            return None
        file = open(filename, "rb")
        ce_error = {}

        for line in file:
            words = line.split()
            if words[6].decode("utf-8") == "CE-ERROR:":
                if words[7].decode("utf-8") == "Getting" and words[8].decode("utf-8") == "counters":
                    ce_error = {
                        "date": words[0].decode("utf-8") + " " + words[1].decode("utf-8") + " " + words[2].decode("utf-8"),
                        "host": words[3].decode("utf-8"),
                        "pci" : words[12].decode("utf-8"),
                        "rank0": 0,
                        "rank1": 0,
                        "rank2": 0,
                        "rank3": 0,
                        "rank4": 0,
                        "rank5": 0,
                        "rank6": 0,
                        "rank7": 0,
                        "node": 0,
                        "source": 0,
                        "cpu": 0,
                        "ha": 0,
                        "mci_status": 0,
                        "mci_status_long": 0,
                        "mci_addr": 0,
                        "mci_addr_long": 0,
                    }
                elif words[7].decode("utf-8").startswith("Rank0="):
                    ce_error["rank0"] = int(words[7].decode("utf-8")[6:],10)
                    ce_error["rank1"] = int(words[8].decode("utf-8")[6:],10)
                    ce_error["rank2"] = int(words[9].decode("utf-8")[6:],10)
                    ce_error["rank3"] = int(words[10].decode("utf-8")[6:],10)
                    ce_error["rank4"] = int(words[11].decode("utf-8")[6:],10)
                    ce_error["rank5"] = int(words[12].decode("utf-8")[6:],10)
                    ce_error["rank6"] = int(words[13].decode("utf-8")[6:],10)
                    ce_error["rank7"] = int(words[14].decode("utf-8")[6:],10)
                    ce_error["node"] = int(words[16].decode("utf-8"))
                    ce_error["source"] = int(words[17].decode("utf-8")[7:],10)
                elif words[7].decode("utf-8") == "status" and words[8].decode("utf-8") == "and" and words[9].decode("utf-8") == "address":
                    ce_error["cpu"] = int(words[12].decode("utf-8")[4:],10)
                    ce_error["ha"] = int(words[13].decode("utf-8")[3:-1],10)
                    ce_error["mci_status"] = int(words[14].decode("utf-8")[11:],10)
                    ce_error["mci_status_long"] = words[15].decode("utf-8")[:-1]
                    ce_error["mci_addr"] = int(words[16].decode("utf-8")[9:],10)
                    ce_error["mci_addr_long"] = words[17].decode("utf-8")
                    syslog_list.append(ce_error)
    return syslog_list

if __name__ == "__main__":
    dlist = syslog_analysis()
    if dlist:
        # print(json.dumps(dlist))
        print_csv(dlist)

