# ***************************** RAG VECTOR STORE *****************************

vector_store = None


# ***************************** SET VECTOR STORE *****************************

def set_vector_store(store):

    global vector_store

    vector_store = store


# ***************************** GET VECTOR STORE *****************************

def get_vector_store():

    return vector_store