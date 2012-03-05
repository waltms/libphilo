import sys
import os
import errno
import philologic
from philologic.Loader import Loader
from philologic.LoadFilters import *
from philologic.Parser import Parser
from philologic.ParserHelpers import *



###########################
## Configuration options ##
###########################

# Define the name of your database: given on the command line by default
dbname = sys.argv[1]

# Define files to load: given on the command line by default
files = sys.argv[2:]

# Define how many cores you want to use
workers = 24

# Define filters as a list of functions to call, either those in Loader or outside
# an empty list is the default
filters = [make_word_counts, generate_words_sorted,make_token_counts,sorted_toms, prev_next_obj, generate_pages, make_max_id]


###########################
## Set-up database load ###
###########################

Philo_Types = ["doc","div","para"] # every object type you'll be indexing.  pages don't count, yet.

XPaths = {  ".":"doc", # Always fire a doc against the document root.
            ".//front":"div",
            ".//div":"div",
            ".//div1":"div",
            ".//div2":"div",
            ".//div3":"div",
            ".//p":"para",
            ".//sp":"para",
            #"stage":"para"
            ".//pb":"page",
         }

Metadata_XPaths = { # metadata per type.  '.' is in this case the base element for the type, as specified in XPaths above.
             "doc" : [(ContentExtractor,"./teiHeader/fileDesc/titleStmt/author","author"),
                      (ContentExtractor,"./teiHeader/fileDesc/titleStmt/title", "title"),
                      (ContentExtractor,"./teiHeader/sourceDesc/biblFull/publicationStmt/date", "date"),
                      (AttributeExtractor,"./text/body/volume@n","volume"),
                      (AttributeExtractor,".@xml:id","id")],
             "div" : [(ContentExtractor,"./head","head"),
                      (AttributeExtractor,".@n","n"),
                      (AttributeExtractor,".@xml:id","id")],
             "para": [(ContentExtractor,"./speaker", "who")],
             "page": [(AttributeExtractor,".@n","n"),
                      (AttributeExtractor,".@src","img")],
           }

os.environ["LC_ALL"] = "C" # Exceedingly important to get uniform sort order.
os.environ["PYTHONIOENCODING"] = "utf-8"

template_destination = "/var/www/philo4/" + dbname
data_destination = template_destination + "/data"

try:
    os.mkdir(template_destination)
except OSError:
    print "The %s database already exists" % dbname
    print "Do you want to delete this database? Yes/No"
    choice = raw_input().lower()
    if choice.startswith('y'):
        os.system('rm -rf %s' % template_destination)
        os.mkdir(template_destination)
    else:
        sys.exit()
os.system("cp -r /var/www/philo4/_system/install_dir/* %s" % template_destination)
os.system("cp /var/www/philo4/_system/install_dir/.htaccess %s" % template_destination)
print "copied templates to %s" % template_destination


####################
## Load the files ##
####################

l = Loader(workers, filters=filters, clean=False)
l.setup_dir(data_destination,files)
l.parse_files(XPaths,Metadata_XPaths)
l.merge_objects()
l.analyze()
l.make_tables()
l.finish(Philo_Types, Metadata_XPaths)
print >> sys.stderr, "done indexing."
