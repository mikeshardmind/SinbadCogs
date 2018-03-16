import subprocess
import threading
import re
from pathlib import Path

PDFTEX = 'pdflatex'
PDFCROP = 'pdfcrop'


class TexRenderer(threading.Thread):

    def __init__(self, *args, **kwargs):
        self.tex = kwargs.pop('tex')
        self.datapath = kwargs.pop('datapath')
        self.dpi = kwargs.pop('dpi', 300)
        self.done = threading.Event()
        self.rendered_files = []
        self.error = None
        super().__init__(*args, **kwargs)

    def run(self):
        try:
            self._render_equations()
        except Exception as e:
            self.error = str(e)
        self.done.set()

    def _render_equations(self):
        names = [
            re.sub('[\W_]', '', n)
            for n in re.findall('%.{,}%\n', self.tex)
        ]
        eqns = re.split('%.{,}%\n', self.tex)[1:]

        for outfile, eq in zip(names, eqns):

            packages, body = [], []
            for eqline in eq.split('\n'):
                if eqline.startswith(r'\usepackage'):
                    packages.append(eqline)
                else:
                    body.append(eqline)

            with open(outfile + '.tex', 'w') as temp:
                temp.write('\documentclass[preview]{standalone}\n')
                [temp.write(pkg + '\n') for pkg in packages]
                temp.write('\\begin{document}\n')
                temp.write('\pagestyle{empty}\n')
                [temp.write(line + '\n') for line in body]
                temp.write('\end{document}\n')

            subprocess.call(
                [PDFTEX, '-interaction=nonstopmode', f'{outfile}.tex']
            )

            # crop pdf, convert to png
            subprocess.call(
                [PDFCROP, f'{outfile}.pdf', f'{outfile}.pdf']
            )

            subprocess.call(
                ['convert',  '-density', f'{self.dpi}',
                 f'{outfile}.pdf',
                 '-background', 'white', '-alpha', 'remove',
                 f'{outfile}.png']
            )

            self.rendered_files.append(f'{outfile}.png')

    def cleanup(self):
        for f in self.rendered_files:
            pattern = f.replace('.png', '.*')
            for _ in Path().glob(pattern):
                _.unlink()
