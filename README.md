# compare-runners

So you're a devops engineer who has been configuring GitLab runner pools for the
engineers and now you need some proof that the jobs are getting faster? I got
you fam.

This tool can scrape through your GitLab projects, collect all the job runtime
statistics and categorise them to different runner configurations per your
approach (datetime periods, runner description regex, etc). It'll generate some
reports with this data as both json and html.

The html report contains some tables representing the runtime and queueing
durations of different jobs per the different runner configurations. This lets
you show that the job is faster or slower depending on the different runner
configuration.

Note: This project is in an infantile stage. Much of the code is hacked
together as I only needed this project to generate some statistical proofs for
work purposes. Code clean up and improvements will come down the pipe later.

## Configuration

Info coming soon on how to write a config.toml to make this tool work.

## Outputs

Info coming soon on how to intepret the outputs.
