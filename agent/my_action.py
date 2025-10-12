from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
import json

@AgentServer.custom_action("my_action_111")
class MyCustomAction(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:

        print("my_action_111 is running!")

        return True

# 运行任务流水线任务
@AgentServer.custom_action("run_pipeline_node")
class RunTaskPipelineAction(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        try:
            # print(f"on RunTaskPipelineAction.run, context: {context}, argv: {argv}")
            pipeline_node_name = json.loads(argv.custom_action_param).get("pipeline_node_name", "")
            print(f"pipeline_node_name: {pipeline_node_name}")
            context.run_task(entry=pipeline_node_name)
            print(f"run pipeline node {pipeline_node_name} success")
            return True
        except Exception as e:
            pipeline_node_name = json.loads(argv.custom_action_param).get("pipeline_node_name", "")
            print(f"run pipeline node {pipeline_node_name} failed, error: {e}")
            return False