from sqlmodel import Session
from typing import List
import backend.crud_db as crud
from backend.models.models_API import UploadDocuments,BaseDocument
from backend.models.models_db import Document,Project,User
from backend.tests.utils.projects import create_random_project
from backend.tests.utils.utils import random_lower_string

def create_random_docs(n_docs:int=1)->List[Document]:
    doc_list=[]
    for _ in range(n_docs):
     filename=random_lower_string()
     doc=BaseDocument(filename=filename,s3_key=random_lower_string())
     doc_list.append(doc)
    return UploadDocuments(documents=doc_list)

def create_random_docs_for_project(db:Session,project_in:Project,creator:User=None,n_docs:int=1)->List[Document]:
    docs=create_random_docs(n_docs)
    if not creator:
        creator=crud.get_project_owner(
            db_session=db,
            project_id=project_in.project_id)
    crud.upload_documents_for_project(db_session=db, user_id=creator.user_id, project_id=project_in.project_id,
                                      upload_docs=docs)
    return project_in.documents




