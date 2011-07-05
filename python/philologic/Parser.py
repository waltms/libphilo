from philologic import OHCOVector, shlaxtree
from philologic.ParserHelpers import *
import re

et = shlaxtree.et  # MAKE SURE you use ElementTree version 1.3.
                   # This is standard in Python 2.7, but an add on in 2.6,
                   # so you have to set the package right at make/configure/install time.
                   # if you did it wrong, you can fix it in shlaxtree or reinstall.

# A list of valid types in the Philo object hierarchy, used to construct an OHCOVector.Stack
# The index is constructed by "push" and "pull" operations to various types, and sending metadata into them.
# Don't try to push or pull byte objects.  we populate it by hand right now.
# Keep your push and pulls matched and nested unless you know exactly what you're doing.

ARTFLVector = ["doc","div1","div2","div3","para","sent","word"]
ARTFLParallels = "page"

# The compressor is NOT configurable in this version, so DON'T change this format.
# Feel free to re-purpose the "page" object to store something else: line numbers, for example.

# The Element -> OHCOVector.Record mapping should be unambiguous, and context-free. 
# They're evaluated relative to the document root--note that if the root is closed and discarded, you're in trouble.
# TODO: add xpath support soon, for attribute matching. <milestone unit='x'>, for example.

TEI_XPaths = {  ".":"doc", # Always fire a doc against the document root.
                ".//front":"div",
                ".//div":"div",
                ".//div0":"div",
                ".//div1":"div",
                ".//div2":"div",
                ".//div3":"div",
                ".//p":"para",
                ".//sp":"para",
                #"stage":"para"
                ".//pb":"page",
             } 

# Relative xpaths for metadata extraction.  look at the constructors in TEIHelpers.py for details.
# Make sure they are unambiguous, relative to the parent object.
# Note that we supply the class and its configuration arguments, but don't construct them yet.
# Full construction is carried out when new records are created, supplying the context and destination.

TEI_MetadataXPaths = { "doc" : [(ContentExtractor,"./teiHeader/fileDesc/titleStmt/author","author"),
                      (ContentExtractor,"./teiHeader/fileDesc/titleStmt/title", "title"),
                      (ContentExtractor,"./teiHeader/profileDesc/creation/date", "date"),                      
                      (AttributeExtractor,".@xml:id","id")],
             "div" : [(ContentExtractor,"./head","head"),
                      (AttributeExtractor,".@n","n"),
                      (AttributeExtractor,".@xml:id","id")],
             "para": [(ContentExtractor,"./speaker", "who")],
             "page": [(AttributeExtractor,".@n","n"),
                      (AttributeExtractor,".@src","img")],
           }

Default_Token_Regexp = r"([^ \.,;:?!\"\n\r\t]+)|([\.;:?!])"

class Parser:
    def __init__(self,known_metadata,docid,format=ARTFLVector,parallel=ARTFLParallels,xpaths=None,metadata_xpaths = None,token_regexp = Default_Token_Regexp,output=None):
        self.known_metadata = known_metadata
        self.docid = docid
        self.i = shlaxtree.ShlaxIngestor(target=self)
        self.tree = None #unnecessary?
        self.root = None
        self.stack = []
        self.map = xpaths or TEI_XPaths
        self.metadata_paths = metadata_xpaths or TEI_MetadataXPaths
        self.v = OHCOVector.CompoundStack(format,parallel,docid,output)
        # OHCOVector should take an output file handle.
        self.extractors = []
        self.file_position = 0
        self.token_regexp = token_regexp
        
    def parse(self,input):
        """Top level function for reading a file and printing out the output."""
        self.input = input
        self.i.feed(self.input.read())
        return self.i.close()
        
    def parsebyline(self,input):
        self.input = input
        for line in self.input:
            self.i.feed(line)
        return self.i.close()

    def feed(self,*event):
        """Consumes a single event from the parse stream.
        
        Transforms "start","text", and "end" events into OHCOVector pushes, pulls, and attributes,
        based on the object and metadata Xpaths given to the constructor."""
        
        e_type, content, offset, name, attrib = event

        if e_type == "start":
            # Add every element to the tree and store a pointer to it in the stack.
            # The first element will be the root of our tree.
            if self.root is None: 
                self.root = et.Element(name,attrib) 
                new_element = self.root
            else:
                new_element = et.SubElement(self.stack[-1],name,attrib)
            self.stack.append(new_element)

            # see if this Element should emit a new Record
            for xpath,ohco_type in self.map.items():
                if new_element in self.root.findall(xpath):
                    if new_element == self.root:
                        new_records = self.v.push(ohco_type,name,offset) 
                        for key,value in self.known_metadata.items():
                            self.v[ohco_type][key] = value
                    else:
                        self.v.push(ohco_type,name,offset) 

                    # Set up metadata extractors for the new Record.
                    # These get called for each child node or text event, until you hit a new record.
                    # We could keep a stack of extractors for multiple simultaneous 
    
                    if ohco_type in self.metadata_paths:
                        self.extractors = []
                        for extractor,pattern,field in self.metadata_paths[ohco_type]:
                            self.extractors.append(extractor(pattern,field,new_element,self.v[ohco_type])) 
                    break   # Don't check any other paths.
                
            # Attribute extraction done after new Element/Record, 
            for e in self.extractors:
                e(new_element,event)

        if e_type == "text":

            # Extract metadata if necessary.
            if self.stack:
                current_element = self.stack[-1]
                for e in self.extractors:
                    e(current_element,event) # EXTRACTORS NEED TO USE NEW STACK API
                    # Should test whether to go on and tokenize or not.
                        
            # Tokenize and emit tokens.  Still a bit hackish.
            # TODO: Tokenizer object shared with output formatter. 
            # Should push a sentence by default here, if we're in a new para/div/doc.  sent byte ordering is not quite right.
            tokens = re.finditer(r"([^ \.,;:?!\"\s\(\)]+)|([\.;:?!])",content,re.U) # should put in a nicer tokenizer.
            for t in tokens:
                if t.group(1):
                    # This will implicitly push a sentence if we aren't in one already.
                    self.v.push("word",t.group(1).lower(),offset + t.start(1)) 
                    self.v.pull("word",offset + t.end(1)) 
                elif t.group(2): 
                    # a sentence should already be defined most of the time.
                    if "sent" not in self.v:
                        self.v.push("sent",t.group(2),offset)
                    self.v["sent"].name = t.group(2) 
                    self.v.pull("sent",offset + t.end(2))

        if e_type == "end":
            if self.stack:
                current_element = self.stack[-1]
                for xpath,ohco_type in self.map.items():
                    # print "matching stack %s against %s for closure" % (self.stack,xpath)
                    if current_element in self.root.findall(xpath):
                        self.v.pull(ohco_type,offset + len(content)) # ADD BYTE
                        break 

            if self.stack: # All elements get pulled of the stack..
                if self.stack[-1].tag == name:
                    old_element = self.stack.pop()
                    # This can go badly out of whack if you're just missing one end tag, 
                    # The OHCOVector is resilient enough to handle it a lot of the time.
                    # Filter your events BEFORE the parser if you have especially ugly HTML or SGML.

                    # prune the tree. saves memory. be careful.
                    old_element.clear() # empty old element.
                    if self.stack: # if the old element had a parent:
                        del self.stack[-1][-1] # delete reference in parent
                        
                    else: # otherwise, you've cleared out the whole tree
                        pass # and should do something clever.
                        # might want to create a new root, and maybe even increment docid?

        self.file_position = offset + len(content)


    def close(self):
        """Finishes parsing a document, and emits any objects still extant.
        
        Returns a max_id vector suitable for building a compression bit-spec in a loader."""
        # pull all extant objects.
        # I think you just need to pull doc and page, now that bytes and parents are set automagically.
        self.v.pull("doc",self.file_position)
        return self.v.v_max


if __name__ == "__main__":
    import sys
    did = 1
    files = sys.argv[1:]
    for docid, filename in enumerate(files,1):
        f = open(filename)
        print >> sys.stderr, "%d: parsing %s" % (docid,filename)
        p = Parser({"filename":filename},docid, output=sys.stdout)
        p.parse(f)
        #print >> sys.stderr, "%s\n%d total tokens in %d unique types." % (spec,sum(counts.values()),len(counts.keys()))
