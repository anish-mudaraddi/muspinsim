import unittest
import numpy as np

from muspinsim.input.asteval import (ASTExpression, ASTExpressionError,
                                     ast_tokenize)
from muspinsim.input.keyword import (MuSpinKeyword, MuSpinEvaluateKeyword,
                                     MuSpinExpandKeyword, InputKeywords)


class TestInput(unittest.TestCase):

    def test_astexpr(self):

        # Start by testing simple expressions
        def double(x):
            return 2*x

        e1 = ASTExpression('x+y+1', variables='xy')

        self.assertEqual(e1.variables, {'x', 'y'})
        self.assertEqual(e1.evaluate(x=2, y=5), 8)

        # Try using a function
        e2 = ASTExpression('double(x)', variables='x',
                           functions={'double': double})

        self.assertEqual(e2.variables, {'x'})
        self.assertEqual(e2.functions, {'double'})
        self.assertEqual(e2.evaluate(x=2), 4)

        # Check that it evaluates when possible
        e3 = ASTExpression('double(4)', functions={'double': double})
        self.assertEqual(e3._store_eval, 8)

        # Errors
        with self.assertRaises(ASTExpressionError):
            e4 = ASTExpression('print(666)')

        with self.assertRaises(ASTExpressionError):
            e5 = ASTExpression('x+1', variables='y')

        with self.assertRaises(ASTExpressionError):
            e1.evaluate()

        # Test tokenization
        ast_tokenize('3.4 2.3 sin(x) atan2(3, 4)')

    def test_keyword(self):

        # Basic keyword
        kw = MuSpinKeyword(['a b c', 'd e f'])

        self.assertTrue((kw.evaluate() == [['a', 'b', 'c'],
                                           ['d', 'e', 'f']]
                         ).all())
        self.assertEqual(len(kw), 2)

        # Test that the default works

        class DefKeyword(MuSpinKeyword):
            default = '1'

        dkw = DefKeyword()

        self.assertEqual(dkw.evaluate()[0][0], '1')

        # Let's try a numerical one
        nkw = MuSpinEvaluateKeyword(['exp(0) 1+1 2**2'])

        self.assertTrue((nkw.evaluate()[0] == [1, 2, 4]).all())

        exkw = MuSpinExpandKeyword(['range(0, 1)', '5.0 2.0'])

        self.assertTrue(len(exkw.evaluate()) == 101)

        # Test expansion of line in longer line

        def _repeat3(x):
            return [x, x, x]

        class RepeatKW(MuSpinExpandKeyword):
            _functions = {
                'repeat3': _repeat3
            }

        rkw = RepeatKW(['repeat3(1)'])

        self.assertTrue((rkw.evaluate()[0] == [1, 1, 1]).all())

        # Some failure cases
        with self.assertRaises(RuntimeError):
            MuSpinKeyword([], args=['a'])  # One argument too much

    def test_input_keywords(self):

        nkw = InputKeywords['name']()

        self.assertEqual(len(nkw.evaluate()[0]), 0)

        skw = InputKeywords['spins']()

        self.assertTrue((skw.evaluate()[0] == ['mu', 'e']).all())

        pkw = InputKeywords['polarization']()

        self.assertTrue((pkw.evaluate()[0] == [1, 0, 0]).all())

        fkw = InputKeywords['field'](['500*MHz'])

        self.assertTrue(np.isclose(fkw.evaluate()[0][0], 1.84449))

        # Test a range of fields
        fkw = InputKeywords['field'](['range(0, 20, 21)'])

        self.assertTrue((np.array([b[0] for b in fkw.evaluate()]) ==
                         np.arange(21)).all())

        tkw = InputKeywords['time']()

        self.assertEqual(len(tkw.evaluate()), 100)
        self.assertEqual(tkw.evaluate()[-1][0], 10.0)

        with self.assertRaises(ValueError):
            ykw = InputKeywords['y_axis'](['something'])

        ykw = InputKeywords['y_axis'](['asymmetry', 'integral'])

        self.assertEqual(ykw.evaluate()[0][0], 'asymmetry')
        self.assertEqual(ykw.evaluate()[1][0], 'integral')

        okw = InputKeywords['orientation'](['zcw(20)'])

        self.assertTrue(len(okw.evaluate()) >= 20)

        zkw = InputKeywords['zeeman'](['0 0 1'], args=['1'])

        self.assertEqual(zkw.id, 'zeeman_1')

        dkw = InputKeywords['dipolar'](['0 0 1'], args=['1', '2'])

        self.assertEqual(dkw.id, 'dipolar_1_2')

        hkw = InputKeywords['hyperfine']([], args=['1'])

        self.assertTrue((hkw.evaluate()[0] == np.zeros((3, 3))).all())

        qkw = InputKeywords['quadrupolar'](['1 0 0',
                                            '0 1 0',
                                            '0 0 cos(1)**2+sin(1)**2'],
                                           args=['1', '2'])

        self.assertTrue((qkw.evaluate()[0] == np.eye(3)).all())

        # Failure case (wrong argument type)
        with self.assertRaises(RuntimeError):
            InputKeywords['zeeman']([], args=['wrong'])
