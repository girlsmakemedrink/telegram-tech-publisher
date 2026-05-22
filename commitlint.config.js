module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'subject-max-length': [2, 'always', 100],
    'body-max-line-length': [1, 'always', 100],
  },
};
