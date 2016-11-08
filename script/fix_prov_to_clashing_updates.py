#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2016, Silvio Peroni <essepuntato@gmail.com>
#
# Permission to use, copy, modify, and/or distribute this software for any purpose
# with or without fee is hereby granted, provided that the above copyright notice
# and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT,
# OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE,
# DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS
# SOFTWARE.

__author__ = 'essepuntato'

import argparse
import os
import re
import rdflib
import shutil
import json
from reporter import Reporter
from rdflib import Graph, ConjunctiveGraph, URIRef, Literal
from rdflib.namespace import RDF, Namespace
import csv
from support import find_paths

context_path = "https://w3id.org/oc/corpus/context.json"
repok = Reporter(True, prefix="[fix_prov.py: INFO] ")
reperr = Reporter(True, prefix="[fix_prov.py: ERROR] ")
repok.new_article()
reperr.new_article()
context_json = {}
PROV = Namespace("http://www.w3.org/ns/prov#")
OCO = Namespace("https://w3id.org/oc/ontology/")
DCTERMS = Namespace("http://purl.org/dc/terms/")
CITO = Namespace("http://purl.org/spar/cito/")
DATACITE = Namespace("http://purl.org/spar/datacite/")
FRBR = Namespace("http://purl.org/vocab/frbr/core#")


def create_update_query(cur_subj_g, update_date, id_dir, dir_split):
    query_string = u"INSERT DATA { GRAPH <%s> { " % cur_subj_g.identifier
    is_first = True
    new_citations = False
    new_ids = False

    for s, p, o in cur_subj_g.triples((None, None, None)):
        if p == CITO.cites or p == FRBR.part:
            new_citations = True
            if not is_first:
                query_string += ". "
            is_first = False
            query_string += u"<%s> <%s> <%s> " % (str(s), str(p), str(o))

    for s, p, o in cur_subj_g.triples((None, DATACITE.hasIdentifier, None)):
        cur_number = long(re.sub("(.+/)([0-9]+)$", "\\2", str(o)))

        # Find the correct directory number where to save the file
        cur_split = 0
        while True:
            if cur_number > cur_split:
                cur_split += dir_split
            else:
                break

        id_se_file_path = \
            id_dir + os.sep + str(cur_split) + os.sep + str(cur_number) + os.sep + "prov" + \
            os.sep + "se" + os.sep + "1.json"
        g_id = load(id_se_file_path)
        if g_id is not None:
            gen_date = g_id.objects(None, PROV.generatedAtTime).next()
            if gen_date == update_date:
                new_ids = True
                if not is_first:
                    query_string += ". "
                is_first = False
                query_string += u"<%s> <%s> <%s> " % (str(s), str(p), str(o))

    return query_string + "} }", new_citations, new_ids


def load(rdf_iri_string, tmp_dir=None):
    res_dir, rdf_file_path = \
        find_paths(rdf_iri_string, args.base + os.sep, "https://w3id.org/oc/corpus/", 10000, 1000)
    
    cur_graph = None

    if os.path.isfile(rdf_file_path):
        try:
            cur_graph = __load_graph(rdf_file_path)
        except IOError:
            if tmp_dir is not None:
                current_file_path = tmp_dir + os.sep + "tmp_rdf_file.rdf"
                shutil.copyfile(rdf_file_path, current_file_path)
                try:
                    cur_graph = __load_graph(current_file_path)
                except IOError as e:
                    reperr.add_sentence("[2] "
                                        "It was impossible to handle the format used for "
                                        "storing the file (stored in the temporary path) '%s'. "
                                        "Additional details: %s"
                                        % (current_file_path, str(e)))
                os.remove(current_file_path)
            else:
                reperr.add_sentence("[3] "
                                    "It was impossible to try to load the file from the "
                                    "temporary path '%s' since that has not been specified in "
                                    "advance" % rdf_file_path)
    else:
        reperr.add_sentence("[4] "
                            "The file specified ('%s') doesn't exist."
                            % rdf_file_path)

    return cur_graph


def __load_graph(file_path):
    errors = ""
    current_graph = ConjunctiveGraph()

    try:
        with open(file_path) as f:
            json_ld_file = json.load(f)
            if isinstance(json_ld_file, dict):
                json_ld_file = [json_ld_file]

            for json_ld_resource in json_ld_file:
                # Trick to force the use of a pre-loaded context if the format
                # specified is JSON-LD
                cur_context = json_ld_resource["@context"]
                json_ld_resource["@context"] = context_json

                current_graph.parse(data=json.dumps(json_ld_resource), format="json-ld")

            return list(current_graph.contexts())[0]
    except Exception as e:
        errors = " | " + str(e)  # Try another format

    raise IOError("[1]", "It was impossible to handle the format used for storing the file '%s'%s" %
                  (file_path, errors))


def store(cur_g, dest_file):
    try:

        cur_json_ld = json.loads(cur_g.serialize(format="json-ld", context=context_json))
        cur_json_ld["@context"] = context_path
        with open(dest_file, "w") as f:
            json.dump(cur_json_ld, f, indent=4)
        repok.add_sentence("File '%s' added." % dest_file)
        return dest_file
    except Exception as e:
        reperr.add_sentence("[5] It was impossible to store the RDF statements in %s. %s" %
                            (dest_file, str(e)))
    
    return None


def get_entity_graph(string_iri, cur_g):
    graph_iri = string_iri.split("/prov/")[0] + "/prov/"
    
    result = Graph(identifier=graph_iri)
    
    prov_graph = cur_g.get_context(URIRef(graph_iri))
    for s, p, o in prov_graph:
        if str(s) == string_iri:
            result.add((s, p, o))
    
    return result


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser("fix_prov.py",
                                         description="This script fixes the bug of having multiple "
                                                     "creation activity for the same resource.")
    arg_parser.add_argument("-i", "--input_file", dest="input", required=True,
                            help="The file containing all the provenance entities that must be modified.")
    arg_parser.add_argument("-b", "--corpus_base_dir", dest="base", required=True,
                            help="The base dir of the corpus.")
    arg_parser.add_argument("-t", "--tmp_dir", dest="tmp_dir",
                            help="The directory for easing the RDF loading.")
    arg_parser.add_argument("-c", "--context", dest="context", required=True,
                            help="The JSON-LD context to use.")

    args = arg_parser.parse_args()

    with open(args.context) as f, open(args.input) as g:
        context_json = json.load(f)
        csv_reader = csv.reader(g)
        
        for res, n_mod, m_type in csv_reader:
            prov_g = load(res)
            prov_entity_g = get_entity_graph(res, prov_g)

            prov_entity = URIRef(res)

            generation_dates = [o for s, p, o in
                                list(g.triples((prov_entity, PROV.generatedAtTime, None)))]
            sources = [o for s, p, o in
                       list(g.triples((prov_entity, PROV.hadPrimarySource, None)))]
            
            # Get all identifiers creation dates and sources
            spec_entity = g.value(prov_entity, PROV.specializationOf)
            res_g = load(str(spec_entity))
            res_entity_g = get_entity_graph(spec_entity, res_g)
            id_gen_date_dict = {}
            for id_entity in [o for s, p, o in
                              list(res_entity_g.triples((spec_entity, DATACITE.hasIdentifier, None)))]:
                id_iri = str(id_entity)
                id_snap_entity = URIRef(id_iri + "/prov/se/1")
                id_snap_g = get_entity_graph(id_snap_entity, load(str(id_snap_entity)))
                new_generation_dates = id_snap_g.value(id_snap_entity, PROV.generatedAtTime)
                new_source = id_snap_g.value(id_snap_entity, PROV.hadPrimarySource)
                id_gen_date_dict[id_snap_entity] = (new_generation_dates, new_source)
                generation_dates += [new_generation_dates]
                sources += [new_source]
            
            generation_dates = sorted(list(set(generation_dates)))
            sources = list(set(sources))
            
            
            
            update_query = list(g.triples((prov_entity, OCO.hasUpdateQuery, None)))[0][2]
    # for cur_dir, cur_subdir, cur_files in os.walk(args.input):
    #     is_se = se_dir in cur_dir
    #     is_ca = ca_dir in cur_dir
    #     if is_ca or is_se:
    #         for cur_file in cur_files:
    #             if cur_file == "2.json":
    #                 if is_se:
    #                     res_file_path = re.sub("^(.+)/%s.*$" % se_dir, "\\1.json", cur_dir)
    #                     cur_g = load(res_file_path)
    #                     se1_file_path = cur_dir + os.sep + "1.json"
    #                     se2_file_path = cur_dir + os.sep + "2.json"
    #                     g_prov_se_1 = load(se1_file_path)
    #                     g_prov_se_2 = load(se2_file_path)
    #                     cur_se_1 = g_prov_se_1.subjects(None, None).next()
    #                     cur_se_2 = g_prov_se_2.subjects(None, None).next()
    #
    #                     # se/1
    #                     invalidation_time = g_prov_se_2.objects(cur_se_2, PROV.generatedAtTime).next()
    #                     new_curatorial_activity = URIRef(cur_se_2.replace("/prov/se/", "/prov/ca/"))
    #                     g_prov_se_1.remove((cur_se_1, PROV.invalidatedAtTime, None))
    #                     g_prov_se_1.add((cur_se_1, PROV.invalidatedAtTime, invalidation_time))
    #                     g_prov_se_1.remove((cur_se_1, PROV.wasInvalidatedBy, None))
    #                     g_prov_se_1.add((cur_se_1, PROV.wasInvalidatedBy, new_curatorial_activity))
    #
    #                     # se/2
    #                     new_update_data = create_update_query(
    #                         cur_g, invalidation_time, args.id_dir, int(args.dir_split))
    #                     g_prov_se_2.remove((cur_se_2, OCO.hasUpdateQuery, None))
    #                     g_prov_se_2.add((cur_se_2, OCO.hasUpdateQuery, Literal(new_update_data[0])))
    #                     g_prov_se_2.remove((cur_se_2, PROV.wasDerivedFrom, None))
    #                     g_prov_se_2.add((cur_se_2, PROV.wasDerivedFrom, cur_se_1))
    #
    #                     # storing
    #                     store(g_prov_se_1, se1_file_path)
    #                     store(g_prov_se_2, se2_file_path)
    #                 else:  # is_ca
    #                     se2_file_path = cur_dir + os.sep + ".." + os.sep + "se" + os.sep + "2.json"
    #                     g_prov_se_2 = load(se2_file_path)
    #                     invalidation_time = g_prov_se_2.objects(None, PROV.generatedAtTime).next()
    #                     res_file_path = re.sub("^(.+)/%s.*$" % ca_dir, "\\1.json", cur_dir)
    #                     cur_g = load(res_file_path)
    #                     new_update_data = create_update_query(
    #                         cur_g, invalidation_time, args.id_dir, int(args.dir_split))
    #
    #                     ca2_file_path = cur_dir + os.sep + "2.json"
    #                     g_prov_ca_2 = load(ca2_file_path)
    #                     cur_ca_2 = g_prov_ca_2.subjects(None, None).next()
    #
    #                     g_prov_ca_2.remove((cur_ca_2, RDF.type, PROV.Create))
    #                     g_prov_ca_2.add((cur_ca_2, RDF.type, PROV.Modify))
    #
    #                     old_description = g_prov_ca_2.objects(cur_ca_2, DCTERMS.description).next()
    #                     new_description = "extended with"
    #                     if new_update_data[1]:
    #                         new_description += " citation data"
    #                         if new_update_data[2]:
    #                             new_description += " and"
    #                     if new_update_data[2]:
    #                         new_description += " new identifiers"
    #
    #                     g_prov_ca_2.remove((cur_ca_2, DCTERMS.description, None))
    #                     g_prov_ca_2.add((cur_ca_2, DCTERMS.description, Literal(
    #                         old_description
    #                             .replace("extended with citation data", new_description)
    #                             .replace("created", new_description))))
    #                     store(g_prov_ca_2, ca2_file_path)
    #
    # # repok.write_file("fix_prov.rep.ok.txt")
    # reperr.write_file("fix_prov.rep.err.txt")
