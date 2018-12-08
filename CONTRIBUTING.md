# Contributing

Hey, thanks for taking an interest in this.

If you'd like to make a pull request, 
please keep the following in mind before doing so

1. Implementing new features should be inquired about before doing.

2. The python source files within conform with [black](https://github.com/ambv/black).
  A makefile (and .bat) are provided for conviniece. 
  These options are correct for the version of black listed in requirements
  Any PRs made should conform to this.

3. Any code which interacts with external APIs must avoid making known bad API requests. 
  Any PR which simplifies code, but ssacrifices this using a try/except block will be rejected.
  (N.B. try/except blocks are still usable, 
  but avoiding the known bad cases first is a requirement if it involves an external service)

4. If your PR resolves or is otherwise related to an open issue, please link to it.

5. If your PR is for i18n support, please read more [here](TRANSLATING.md)

Thanks again!