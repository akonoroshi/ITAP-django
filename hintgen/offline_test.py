import json, random, os
import django
django.setup()
from hintgen.models import Course, Problem, Student, SourceState, State, Testcase
from hintgen.getHint import get_hint, run_tests

RUNNING_STUDY = False

def unpack_code_json(data, course_name, problem_name):
    try:
        course_id = int(course_name)
        course = Course.objects.filter(id=course_id)
        if len(course) != 1:
            raise NameError("No course exists with that ID")
    except:
        course = Course.objects.filter(name=course_name)
        if len(course) != 1:
            raise NameError("No course exists with that name")
    course = course[0]

    try:
        problem_id = int(problem_name)
        problem = Problem.objects.filter(id=problem_id)
        if len(problem) != 1:
            raise NameError("No problem exists with that ID")
    except:
        problem = Problem.objects.filter(name=problem_name)
        if len(problem) != 1:
            raise NameError("No problem exists with that name")
    problem = problem[0]

    student = Student.objects.filter(name=data["student_id"])
    if len(student) == 0:
        # We haven't seen this student before, but it's okay; we can add them

        # SORRY HARDCODED STUDY STUFF
        condition = "hints_first" if random.random() < 0.5 else "hints_second"

        student = Student(course=course, name=data["student_id"], condition=condition)
        student.save()
    elif len(student) > 1:
        # Multiple students with the same name! Uh oh.
        raise NameError("Could not disambiguate student name; please modify database")
    else:
        student = student[0]

        if student.condition not in ["hints_first", "hints_second"]:
            condition = "hints_first" if random.random() < 0.5 else "hints_second"
            student.condition = condition
            student.save()


    data["course"] = course
    data["problem"] = problem
    data["student"] = student
    # Clean up return carriages
    data["code"] = data["code"].replace("\r\n", "\n").replace("\n\r", "\n").replace("\r", "\n")
    return data

"""
Given code, generate a hint for that code.

USAGE
In the url, map:
    course_id -> the course ID for this submission
    problem_id -> the problem ID for this submission
In the request content, include a json object mapping:
    student_id -> the student ID for this submission
    code -> the code being submitted

RETURNS
A json object mapping:
    hint_message -> a string containing the resulting hint message
    hint_type -> the type of hint that was generated
    line -> the line number the hint occurs on
    col -> the column number the hint occurs on
"""
def hint(data, course_id, problem_id):
    data = unpack_code_json(data, course_id, problem_id)

    code_state = SourceState(code=data["code"], problem=data["problem"], 
                             student=data["student"], count=1)

    if RUNNING_STUDY:
        # Some terrible hard coding for the Spring '17 study. Sorry!
        first_half = [ "has_two_digits", "is_leap_month", "wear_a_coat", 
                      "multiply_numbers", "sum_of_odd_digits", "any_divisible",
                      "has_balanced_parentheses", "find_the_circle" ]
        second_half = [ "was_lincoln_alive", "get_extra_bagel", "go_to_gym", 
                        "one_to_n", "reduce_to_positive", "any_first_chars",
                        "second_largest", "last_index" ]
        if (data["problem"].name in first_half and data["student"].condition == "hints_first") or \
            (data["problem"].name in second_half and data["student"].condition == "hints_second"):
            code_state = get_hint(code_state)
            hint_message = code_state.hint.message.replace("\n", "<br>").replace("    ", "&nbsp;&nbsp;&nbsp;&nbsp;").replace("\t", "&nbsp;&nbsp;&nbsp;&nbsp;").replace("  ", "&nbsp;&nbsp;")
            result_object = { "hint_message" : hint_message, "line" : code_state.hint.line,
                              "col" : code_state.hint.col, "hint_type" : code_state.hint.level }
        else:
            code_state = run_tests(code_state)
            test_results = code_state.feedback.replace("\n", "<br>").replace("    ", "&nbsp;&nbsp;&nbsp;&nbsp;").replace("\t", "&nbsp;&nbsp;&nbsp;&nbsp;").replace("  ", "&nbsp;&nbsp;")
            result_object = { "hint_message" : "Here's the test case results:<br>" + test_results, 
                              "line" : 1, "col" : 1, "hint_type" : "feedback" }
    else:
        code_state = get_hint(code_state)
        hint_message = code_state.hint.message.replace("\n", "<br>").replace("    ", "&nbsp;&nbsp;&nbsp;&nbsp;").replace("\t", "&nbsp;&nbsp;&nbsp;&nbsp;").replace("  ", "&nbsp;&nbsp;")
        result_object = { "hint_message" : hint_message, "line" : code_state.hint.line,
                          "col" : code_state.hint.col, "hint_type" : code_state.hint.level }
    return result_object

"""
Sets up a problem which can then be used for feedback and hint generation.

USAGE
Request data should be a json object which includes the maps:
    name -> a string representing the name of the problem (what the function should be called)
    courses -> a list of course IDs you want to associate this problem with. The courses should already exist in the system
    tests -> a list of dictionaries, where each dictionary contains test case info:
        input -> a string which, when evaluated with eval(), turns into a tuple containing arguments
        output -> a string which, when evaluated with eval(), turns into the value that the function should return, given input
        extra -> optional. if extra is mapped to "check_copy", the test case will check to make sure that the input isn't modified
    solution_code -> a string containing a code solution to the problem. Must pass all the given test cases!
    arguments -> optional. a dictionary that maps function names to lists of the argument types they expect (represented as strings). If the argument type can vary, it can be represented with "None"
    given_code -> optional. a string containing given code that is provided and should be included when testing a student's submission.

RETURNS
A json object mapping:
    problem_id -> the problem's new ID
"""
def setup_problem(name: str, courses: list, tests: list, solution_code: str, arguments={ }, given_code=""):

    problem = Problem(name=name)
    problem.arguments = str(arguments)
    """
    if arguments != { }:
        problem.arguments = str(arguments)
    else:
        problem.arguments = "{ }"
    """
    
    if given_code != "":
        problem.given_code = given_code

    problem.save()
    problem.courses.add(*courses)

    # Set up new test cases
    test_objects = []
    for test in tests:
        if "input" not in test:
            problem.delete()
            raise TypeError("Input missing from one or more test cases")
        if "output" not in test:
            problem.delete()
            raise TypeError("Output missing from one or more test cases")
        t = Testcase(problem=problem, test_input=test["input"], test_output=test["output"])
        if "extra" in test:
            t.test_extra = test["extra"]
        test_objects.append(t)
    for t in test_objects:
        t.save()

    # Set up teacher solution
    admin = Student.objects.get(id=1) # admin account
    teacher_solution = SourceState(code=solution_code, problem=problem, 
                                   count=1, student=admin)
    teacher_solution = run_tests(teacher_solution)
    if teacher_solution.score != 1:
        feedback = teacher_solution.feedback
        problem.delete()
        for test in test_objects:
            test.delete()
        teacher_solution.delete()
        raise ValueError("The provided solution does not pass the provided test cases. Please try again. Failing feedback: " + feedback)

    return problem.id

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "..testsite.settings")
    course_ids = [1]
    test_cases = [{'input': '(22, True)', 'output': 'False'}, {'input': '(20, False)', 'output': 'False'}, {'input': '(21, False)', 'output': 'True'}]
    solution_code = "def canDrinkAlcohol(age, isDriving):\n    return age >= 21 and not isDriving\n"
    problem_id = setup_problem('canDrinkAlcohol', course_ids, test_cases, solution_code)
    data = {'student_id' : 'tester', 'code' : "def canDrinkAlcohol(age, isDriving):\n    return age > 21 and not isDriving\n" }
    print(hint(data, 1, problem_id))