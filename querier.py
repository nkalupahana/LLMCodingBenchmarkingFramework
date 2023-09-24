from abc import ABC, abstractmethod
from typing import Dict, List, Union, Optional, Any
from llm_types import *
import openai
import os
import sys
import subprocess

class AIModelQuerier(ABC):
	"""
	Abstract base class for AI models.
	"""
	
	def __init__(self, model_identifier: str):
		self._model_identifier = model_identifier
	
	@property
	def model_identifier(self) -> str:
		"""
		A unique identifier for the model.
		"""
		return self._model_identifier
	
	@classmethod
	def supported_model_names(cls):
		return []
		
	@abstractmethod
	def generate_solution(self, problem_input: LLMProblemInput) -> 'LLMSolution':
		"""
		Generates a solution for the given problem definition.
		
		Subclasses should override this method to provide the logic for
		generating solutions.
		
		:param problem_definition: The problem definition for which to generate a solution.
		:return: An LLMSolution object containing the generated solution.
		"""
		pass
	
	@classmethod
	def resolve_model_names(cls, model_names: List[str]) -> List['AIModelQuerier']:
		subclass_mapping = {model_name: subclass for subclass in cls.__subclasses__() 
							for model_name in subclass.supported_model_names()}
		instances = []
		for model_name in model_names:
			subclass = subclass_mapping.get(model_name, HumanAIModelQuerier)
			instances.append(subclass(model_name))
		return instances
	
	@classmethod
	def construct_textual_prompt(cls, llm_problem_input: LLMProblemInput) -> str:
		# Start with the textual prompt
		prompt_text = llm_problem_input.prompt
	
		# Add function prototype if available
		function_prototype = llm_problem_input.function_prototype
		if function_prototype:
			prompt_text += f"\n\nFunction Signature:\n{str(function_prototype)}"
	
		# Add sample inputs and outputs if available
		sample_io = llm_problem_input.sample_inputs_outputs
		if sample_io:
			sample_io_text = '\n\nSample Inputs and Outputs:\n'
			for i, test_case in enumerate(sample_io, start=1):
				sample_io_text += f"\nTest Case {i}:\n{str(test_case)}"
			prompt_text += sample_io_text
	
		# Add input code if available
		input_code = llm_problem_input.input_code
		if input_code:
			prompt_text += f"\n\nInput Code:\n{input_code}"
	
		return prompt_text

	def __str__(self) -> str:
		return f"{self.__class__.__name__}(model_identifier={self.model_identifier})"

class HumanAIModelQuerier(AIModelQuerier):	
	def generate_solution(self, problem_input: LLMProblemInput) -> 'LLMSolution':
		prompt = AIModelQuerier.construct_textual_prompt(problem_input)
		print(prompt)
		
		# Copy to pasteboard
		process = subprocess.Popen('pbcopy', universal_newlines=True, stdin=subprocess.PIPE)
		process.communicate(prompt)
		process.wait()

		lines = []
		try:
			for line in sys.stdin:
				lines.append(line)
		except EOFError:
			pass
		response = "".join(lines)

		
		return LLMSolution(problem_input.problem_id, "human", problem_input.prompt_id, response)

class OpenAIModelQuerier(AIModelQuerier):
	@classmethod
	def supported_model_names(cls):
		# Make sure this key is set before trying to interact with the OpenAI API
		if 'OPENAI_API_KEY' in os.environ:
			response = openai.Model.list()
			return [item['id'] for item in response['data']]
		else:
			print("Warning: No OpenAI API key found in environment.")
			return []
			
	def generate_solution(self, problem_input: LLMProblemInput) -> 'LLMSolution':
		prompt = AIModelQuerier.construct_textual_prompt(problem_input)
		# Send the prompt to the OpenAI API
		response = openai.Completion.create(
			engine=self.model_identifier,
			prompt=prompt,
			max_tokens=1000
		)
		
		# Extract the generated code
		response = response.choices[0].text.strip()
		return LLMSolution(problem_input.problem_id, self.model_identifier, problem_input.prompt_id, response)


	