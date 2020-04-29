# Contributing

Hey, thanks for taking an interest in this.

If you'd like to make a pull request or contribute issue wise
please keep the following in mind before doing so

1. It is unlikely that any new features will be added. This repo is largely in maintenence only mode.

2. The python source files within conform with [black](https://github.com/ambv/black).
  A makefile (and .bat) are provided for conviniece. 
  These options are correct for the version of black listed in requirements
  Any PRs made should conform to this.

3. Any code which interacts with external APIs must avoid making known bad API requests. 
  Any PR which simplifies code, but sacrifices this using a try/except block will be rejected.
  (N.B. try/except blocks are still usable,
  but avoiding the known bad cases first is a requirement if it involves an external service)

4. If your PR resolves or is otherwise related to an open issue, please link to it.

5. If it's not about the technical portion of the code, please refrain from commenting unless your opinion has been solicited directly by a code owner.

6. If you have a personal issue, leave it at the door. It won't be given an audience here.

Thanks again!
