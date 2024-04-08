# Example of how to apply the decorator with dependency injection
@injector.inject
@publish_before(topic="before_execution")
def my_function(data: int) -> int:
    print(f"Executing my_function with data: {data}")
    return data * 2
