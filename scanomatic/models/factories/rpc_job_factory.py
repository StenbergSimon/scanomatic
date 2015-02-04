import scanomatic.models.rpc_job_models as rpc_job_models
from scanomatic.generics.abstract_model_factory import AbstractModelFactory
from scanomatic.generics.model import Model

class RPC_Job_Model_Factory(AbstractModelFactory):

    _MODEL = rpc_job_models.RPCjobModel 

    @classmethod
    def _validate_pid(cls, model):

        if model.pid is None or isinstance(model.pid, int) and model.pid > 0:

            return True

        return model.FIELD_TYPES.pid

    @classmethod
    def _validate_id(cls, model):

        if isinstance(model.id, str):
    
            return True

        #TODO: Add verification of uniqueness?
        return model.FIELD_TYPES.id

    @classmethod
    def _validate_type(cls, model):

        if model.type in rpc_job_models.JOB_TYPE:

            return True

        return model.FIELD_TYPES.type

    @classmethod
    def _validate_status(cls, model):

        if model.status in rpc_job_models.JOB_STATUS:

            return True

        return model.FIELD_TYPES.model

    @classmethod
    def _vaildate_content_model(cls, model):

        if isinstance(model.contentModel, Model):

            return True

        return model.FIELD_TYPES.contentModel
