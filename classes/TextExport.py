# Modified by: Stephen Meisenbacher
# source: https://github.com/MuckRock
# classes for DocumentCloud AddOns

"""
This add-on allows you to bulk export PDFs from DocumentCloud
"""

import zipfile
import logging
from documentcloud.addon import AddOn


class TextExport(AddOn):
    """Export all of the selected documents' text in a zip file"""

    def main(self):
        logging.getLogger("messages").info("TEXT EXPORT: reading documents for project={}".format(self.data['proj_id']))
        project = self.client.projects.get(self.data['proj_id'])
        doc_ids = project.document_ids
        to_process = len(doc_ids)
        logging.getLogger("messages").info("TEXT EXPORT: {} documents found".format(to_process))
        self.set_progress(0)
        with zipfile.ZipFile("{}_import.zip".format(project.title), mode="w") as archive:
            for i, doc_id in enumerate(doc_ids):
                print("{}:{}".format(i, doc_id), flush=True)
                document = self.client.documents.get(doc_id)
                with archive.open("{}.txt".format(document.slug), "w") as txt:
                    txt.write(document.full_text)
                self.set_progress(100 * (i+1) // to_process)
        logging.getLogger("messages").critical("TEXT EXPORT: import complete")
        self.upload_file(open("{}_import.zip".format(project.title)))

if __name__ == "__main__":
    TextExport().main()