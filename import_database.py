import pyodbc as odbc

def import_database(dbname):

    count = 0
    with open("out.rdf", "r") as f:
        for line in f:
            print line
            count += 1
            if count >= 100:
                break

if __name__ == "__main__":
    import_database("DBLP")